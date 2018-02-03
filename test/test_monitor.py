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

from ttt.watcher import Watcher
from ttt.watcher import WatchState
from ttt.monitor import Monitor
from ttt.monitor import Operations
from ttt.monitor import create_monitor
from ttt.reporter import Reporter

@contextmanager
def chdir(path):
    old_dir = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(old_dir)

class TestMonitor:
    def teardown(self):
        TempDirectory.cleanup_all()

    def test_create_with_invalid_watch_area(self):
        error = None
        bad_path = os.path.abspath(os.path.sep + os.path.join('bad', 'path'))
        try:
            create_monitor(bad_path)
        except IOError as e:
            error = e
        assert 'Invalid path: {bad} ({bad})'.format(bad=bad_path) in str(error)

    def test_create_monitor_default_paths(self):
        m = create_monitor()
        cwd = os.getcwd()
        assert len(m.reporters) == 1
        reporter = m.reporters[0]
        assert reporter.watch_path == cwd
        assert reporter.build_path == '{}-build'.format(os.path.join(cwd, os.path.basename(cwd)))

    def test_create_monitor_with_watch_path(self):
        wd = TempDirectory()
        source_path = wd.makedir('source')
        build_path = wd.makedir('build')

        with chdir(wd.path):
            m = create_monitor(source_path)
        assert len(m.reporters) == 1
        reporter = m.reporters[0]
        assert reporter.watch_path == source_path
        assert reporter.build_path == '{}-build'.format(os.path.realpath(source_path))

    def test_create_monitor_with_watch_and_build_path(self):
        wd = TempDirectory()
        source_path= wd.makedir('source')
        build_path = wd.makedir('build')

        with chdir(wd.path):
            m = create_monitor(source_path, build_path=os.path.basename(build_path))
        assert len(m.reporters) == 1
        reporter = m.reporters[0]
        assert reporter.watch_path == source_path
        assert reporter.build_path == '{}'.format(os.path.realpath(build_path))

    def test_poll_build_test(self):
        reporter = MagicMock(spec=Reporter)
        watcher = MagicMock()
        builder = MagicMock()
        executor = MagicMock()
        watcher.poll = MagicMock(return_value=WatchState(set(['change']), set(), set(), 0))
        executor.test = MagicMock(return_value={'total_failed':0})
        m = Monitor(watcher, builder, executor, [reporter], interval=0)

        m.run(step=True)

        assert 'poll' in [ c for c,a,kw in watcher.mock_calls ]
        # build step is captured as ''
        assert [ c for c,a,kw in builder.mock_calls ] == ['']
        assert [ c for c,a,kw in executor.mock_calls ] == ['test']
        assert [ c for c,a,kw in reporter.mock_calls ] == [
            'report_watchstate',
            'session_start', # build
            'report_build_path',
            'session_end', # build
            'session_start', # test
            'report_results',
            'session_end', # test
            'wait_change'
        ]

    def test_test_again_on_fix(self):
        reporter = MagicMock(spec=Reporter)
        o = watcher = builder = executor = MagicMock()
        watcher.poll = MagicMock(return_value=WatchState(set(['change']), set(), set(), 0))
        executor.test = MagicMock(return_value={'total_failed':1})
        m = Monitor(watcher, builder, executor, [reporter], interval=0)
        m.run(step=True)

        o.reset_mock()

        executor.test = MagicMock(return_value={'total_failed':0})

        m.run(step=True)

        assert len([ c for c,a,kw in o.method_calls if c == 'test' ]) == 2

    def test_keyboardinterrupt_during_poll(self):
        reporter = MagicMock(spec=Reporter)
        watcher = MagicMock()
        o = builder = executor = MagicMock()
        m = Monitor(watcher, builder, executor, [reporter], interval=0)

        o.reset_mock()

        watcher.poll = MagicMock(
            return_value=WatchState(set(['change']), set(), set(), 0),
            side_effect=KeyboardInterrupt
        )

        m.run(step=True)

        assert 'poll' in [ c for c,a,kw in watcher.method_calls ]
        assert [ c for c,a,kw in reporter.method_calls ] == [ 'interrupt_detected' ]

    def test_keyboardinterrupt_during_wait(self):
        reporter = MagicMock(spec=Reporter)
        o = watcher = builder = executor = MagicMock()
        watcher.poll = MagicMock(return_value=WatchState(set(), set(), set(), 0))
        m = Monitor(watcher, builder, executor, [reporter], interval=0)

        o.reset_mock()
        with patch('time.sleep', autospec=True, side_effect=KeyboardInterrupt):
            m.run(step=True)

        call_filter = set([ 'interrupt_detected', 'halt' ])
        calls = [ c for c,a,kw in reporter.method_calls if c in call_filter ]
        assert calls == [ 'interrupt_detected', 'halt' ]

    def test_continue_after_wait_interrupt(self):
        reporter = MagicMock(spec=Reporter)
        o = watcher = builder = executor = MagicMock()
        watcher.poll = MagicMock(return_value=WatchState(set(), set(), set(), 0))
        m = Monitor(watcher, builder, executor, [reporter], interval=0)

        o.reset_mock()
        m.run(step=True)
        with patch('time.sleep', autospec=True, side_effect=Interrupter(1)):
            m.run(step=True)

        call_filter = set([ 'interrupt_detected', 'halt' ])
        calls = [ c for c,a,kw in reporter.method_calls if c in call_filter ]
        assert calls == [ 'interrupt_detected' ]

    def test_keyboardinterrupt_during_operations(self):
        def builder():
            raise KeyboardInterrupt

        reporter = MagicMock(spec=Reporter)
        o = watcher = executor = MagicMock()
        watcher.poll = MagicMock(
            return_value=WatchState(set(['change']), set(), set(), 0)
        )
        m = Monitor(watcher, builder, executor, [reporter], interval=0)

        o.reset_mock()
        m.run(step=True)

        assert 'interrupt_detected' in set([ c for c,a,kw in reporter.method_calls])

    def test_builderror(self):
        import subprocess
        def builder():
            subprocess.check_output("false")

        reporter = MagicMock(spec=Reporter)
        o = watcher = executor = MagicMock()
        watcher.poll = MagicMock(return_value=WatchState(set(['change']), set(), set(), 0))
        m = Monitor(watcher, builder, executor, [reporter], interval=0)

        o.reset_mock()
        m.run(step=True)

        calls = set([ c for c,a,kw in o.method_calls ])
        assert 'test' not in calls
        assert 'report_build_failure' in [ c for c,a,kw in reporter.method_calls ]

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

