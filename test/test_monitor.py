#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
test_monitor
----------------------------------

Tests for `monitor` module.
"""
import os
import termstyle

from contextlib import contextmanager
from testfixtures import TempDirectory
try:
    from mock import Mock, MagicMock, call, patch
except:
    from unittest.mock import Mock, MagicMock, call, patch

from ttt.systemcontext import SystemContext
from ttt.watcher import Watcher
from ttt.watcher import WatchState
from ttt.monitor import Monitor
from ttt.monitor import Operations
from ttt.watcher import InvalidWatchArea
from ttt.monitor import create_monitor

@contextmanager
def chdir(path):
    old_dir = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(old_dir)

class MockContext(SystemContext):
    def __init__(self):
        super(MockContext, self).__init__()
        self.output = ''

    def getvalue(self):
        return self.output

    def write(self, string):
        self.output += string

    def walk(self, root):
        return []

class TestMonitor:
    def teardown(self):
        TempDirectory.cleanup_all()

    def test_create_with_invalid_watch_area(self):
        c = MockContext()
        error = None
        bad_path = os.path.abspath(os.path.sep + os.path.join('bad', 'path'))
        try:
            create_monitor(c, bad_path)
        except InvalidWatchArea as e:
            error = e
        assert str(error) == 'Invalid path: {bad} ({bad})'.format(bad=bad_path)

    def test_create_monitor_default_paths(self):
        m = create_monitor(MagicMock())
        cwd = os.getcwd()
        assert m.watcher.watch_path == cwd
        assert m.builder.build_path == '{}-build'.format(os.path.join(cwd, os.path.basename(cwd)))

    def test_create_monitor_with_watch_path(self):
        wd = TempDirectory()
        source_path = wd.makedir('source')
        build_path = wd.makedir('build')

        with chdir(wd.path):
            m = create_monitor(MagicMock(), source_path)
        assert m.watcher.watch_path == source_path
        assert m.builder.build_path == '{}-build'.format(os.path.realpath(source_path))

    def test_create_monitor_with_watch_and_build_path(self):
        wd = TempDirectory()
        source_path= wd.makedir('source')
        build_path = wd.makedir('build')

        with chdir(wd.path):
            m = create_monitor(MagicMock(), source_path, build_path=os.path.basename(build_path))
        assert m.watcher.watch_path == source_path
        assert m.builder.build_path == '{}'.format(os.path.realpath(build_path))

    def test_poll_build_test(self):
        o = watcher = builder = executor = reporter = MagicMock()
        watcher.poll = MagicMock(return_value=WatchState(['change']))
        executor.test = MagicMock(return_value={'total_failed':0})
        m = Monitor(watcher, builder, executor, reporter, interval=0)

        o.reset_mock()

        m.run(step=True)
        call_filter = set([ 'poll', 'build', 'test', 'wait_change' ])
        calls = [ c for c,a,kw in o.method_calls if c in call_filter ]
        assert calls == [ 'poll', 'build', 'test', 'wait_change' ]

    def test_test_again_on_fix(self):
        o = watcher = builder = executor = reporter = MagicMock()
        watcher.poll = MagicMock(return_value=WatchState(['change']))
        executor.test = MagicMock(return_value={'total_failed':1})
        m = Monitor(watcher, builder, executor, reporter, interval=0)
        m.run(step=True)

        o.reset_mock()

        executor.test = MagicMock(return_value={'total_failed':0})

        m.run(step=True)

        call_filter = set([ 'poll', 'build', 'test', 'wait_change' ])
        calls = [ c for c,a,kw in o.method_calls if c in call_filter ]
        assert calls == [ 'poll', 'build', 'test', 'test', 'wait_change' ]

    def test_keyboardinterrupt_during_poll(self):
        o = watcher = builder = executor = reporter = MagicMock()
        m = Monitor(watcher, builder, executor, reporter, interval=0)

        o.reset_mock()

        watcher.poll = MagicMock(return_value=WatchState(['change']), side_effect=KeyboardInterrupt)

        m.run(step=True)

        call_filter = set([ 'poll', 'build', 'test', 'wait_change', 'report_interrupt' ])
        calls = [ c for c,a,kw in o.method_calls if c in call_filter ]
        assert calls == [ 'poll', 'report_interrupt' ]

    def test_keyboardinterrupt_during_wait(self):
        o = watcher = builder = executor = reporter = MagicMock()
        watcher.poll = MagicMock(return_value=WatchState())
        m = Monitor(watcher, builder, executor, reporter, interval=0)

        o.reset_mock()
        with patch('time.sleep', autospec=True, side_effect=KeyboardInterrupt):
            m.run(step=True)

        call_filter = set([ 'interrupt_detected', 'halt' ])
        calls = [ c for c,a,kw in o.method_calls if c in call_filter ]
        assert calls == [ 'interrupt_detected', 'halt' ]

    def test_continue_after_wait_interrupt(self):
        o = watcher = builder = executor = reporter = MagicMock()
        watcher.poll = MagicMock(return_value=WatchState())
        m = Monitor(watcher, builder, executor, reporter, interval=0)

        o.reset_mock()
        m.run(step=True)
        with patch('time.sleep', autospec=True, side_effect=Interrupter(1)):
            m.run(step=True)

        call_filter = set([ 'interrupt_detected', 'halt' ])
        calls = [ c for c,a,kw in o.method_calls if c in call_filter ]
        assert calls == [ 'interrupt_detected' ]

    def test_keyboardinterrupt_during_operations(self):
        o = watcher = builder = executor = reporter = MagicMock()
        watcher.poll = MagicMock(return_value=WatchState(['change']))
        builder.build = MagicMock(side_effect=Interrupter(1))
        m = Monitor(watcher, builder, executor, reporter, interval=0)

        o.reset_mock()
        m.run(step=True)

        call_filter = set([ 'poll', 'build', 'test', 'wait_change', 'report_interrupt' ])
        calls = [ c for c,a,kw in o.method_calls if c in call_filter ]
        assert calls == [ 'poll', 'build', 'report_interrupt' ]

    def test_builderror(self):
        def build_error():
            from ttt.builder import BuildError
            from collections import namedtuple
            FakeException = namedtuple('FakeException', 'cmd')
            raise BuildError(FakeException(cmd='boom'))

        o = watcher = builder = executor = reporter = MagicMock()
        watcher.poll = MagicMock(return_value=WatchState(['change']))
        builder.build = MagicMock(side_effect=build_error)
        m = Monitor(watcher, builder, executor, reporter, interval=0)

        o.reset_mock()
        m.run(step=True)

        call_filter = set([ 'poll', 'build', 'test', 'wait_change', 'report_interrupt' ])
        calls = [ c for c,a,kw in o.method_calls if c in call_filter ]
        assert calls == [ 'poll', 'build', 'wait_change' ]

class Interrupter:
    def __init__(self, count):
        self.count = count
    def __call__(self, *args, **kwargs):
        count = self.count
        self.count -= 1
        if count > 0:
            raise KeyboardInterrupt()

class TestUtils:
    def test_first_value(self):
        from ttt.monitor import first_value

        assert first_value() == None
        assert first_value(1) == 1
        assert first_value(1, 2) == 1
        assert first_value(None, 1) == 1
        assert first_value(None, None, 1) == 1
