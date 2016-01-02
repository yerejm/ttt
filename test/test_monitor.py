#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
test_monitor
----------------------------------

Tests for `monitor` module.
"""
import os
import termstyle

import pytest
from testfixtures import TempDirectory

from ttt.systemcontext import SystemContext
from ttt.watcher import Watcher
from ttt.watcher import create_watchstate
from ttt.monitor import Monitor
from ttt.monitor import Operations
from ttt.watcher import InvalidWatchArea
from ttt.monitor import create_monitor

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

    # def test_create_with_build_path(self):
    #     c = MockContext()
    #     m = create_monitor(c, os.getcwd(), build_path='build')
    #     assert m.build_path == os.path.join(os.getcwd(), 'build')
    #
    # def test_create(self):
    #     c = MockContext()
    #     m = create_monitor(c, os.getcwd(), build_path='build')
    #     assert m.build_path == os.path.join(os.getcwd(), 'build')
    #     assert m.runstate.active()

    # def test_run(self):
    #     work_directory = TempDirectory()
    #     work_directory.write('a.h', b'')
    #     work_directory.write('a.c', b'')
    #     work_directory.write('a.cc', b'')
    #     work_directory.write('CMakeLists.txt', b'')
    #     work_directory.write('blah.txt', b'')
    #
    #     sc = SystemContext()
    #     w = Watcher(sc, work_directory.path)
    #     o = MockOperations()
    #     m = create_monitor(sc, operations=o, watcher=w)
    #     work_directory.write('b.c', b'')
    #
    #     try:
    #         m.run()
    #     except StopTestException:
    #         pass
    #     assert o.operations() == [
    #             m.report_change(create_watchstate()),
    #             m.build(),
    #             m.test(),
    #             ]

class MockOperations(Operations):
    def __init__(self):
        super(MockOperations, self).__init__()

    # def __getattr__(self, method_name):
    #     def fn(*args, **kwargs):
    #         self.calls.append(method_name)
    #     return fn

    def run(self):
        raise StopTestException()

class StopTestException(Exception):
    pass

class TestUtils:
    def test_first_value(self):
        from ttt.monitor import first_value

        assert first_value() == None
        assert first_value(1) == 1
        assert first_value(1, 2) == 1
        assert first_value(None, 1) == 1
        assert first_value(None, None, 1) == 1

class TestOperations:
    def test_append(self):
        def fna():
            pass
        def fnb():
            pass

        o = Operations()
        o.append(fna)
        o.append(fnb)
        assert o.operations() == [fna, fnb]

    def test_reset(self):
        def fna():
            pass
        def fnb():
            pass

        o = Operations()
        o.append(fna)
        o.append(fnb)
        o.reset()
        assert o.operations() == []

    def test_run(self):
        def make_fn(run, x):
            def fn():
                run.append(x)
            return fn

        run = []
        o = Operations()
        o.append(make_fn(run, 1))
        o.append(make_fn(run, 2))
        o.run()
        assert run == [1, 2]
        assert o.operations() == []

