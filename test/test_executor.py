#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
test_executor
----------------------------------

Tests for `executor` module.
"""
import os
import re
import io
import sys
import stat

from testfixtures import TempDirectory
from contextlib import contextmanager

from ttt.executor import Executor
from ttt.systemcontext import SystemContext

@contextmanager
def stdout_redirector(stream):
    old_stdout = sys.stdout
    sys.stdout = stream
    try:
        yield
    finally:
        sys.stdout = old_stdout

class MockContext(SystemContext):
    def __init__(self, files=[], results=[]):
        self.files = files
        self.results = results[::-1]
        self.command = []

    def streamed_call(self, command, listener):
        self.command.append(command)
        if self.results:
            results = self.results.pop()
            for line in results:
                listener(line)

    def walk(self, path):
        for x, y, z in self.files:
            yield x, y, z

BUILDPATH = os.path.join('', 'path', 'to', 'build')
DUMMYPATH = os.path.join(BUILDPATH, 'test_core')

class TestExecutor:
    def test_passed(self):
        testdict = { 'test_core': 'test_core.c' }
        sc = MockContext(
                [[BUILDPATH, 'test_core', stat.S_IXUSR]],
                [[
                    '[==========] Running 1 test from 1 test case.\n',
                    '[----------] Global test environment set-up.\n',
                    '[----------] 1 test from core\n',
                    '[ RUN      ] core.ok\n',
                    '[       OK ] core.ok (0 ms)\n',
                    '[----------] 1 test from core (0 ms total)\n',
                    '\n',
                    '[----------] Global test environment tear-down\n',
                    '[==========] 1 test from 1 test case ran. (0 ms total)\n',
                    '[  PASSED  ] 1 test.\n',
                ]]
            )
        e = Executor(sc)
        f = io.StringIO()
        with stdout_redirector(f):
            results = e.test(BUILDPATH, testdict)
        test = next(iter(results))
        assert test.failures() == []
        assert f.getvalue() == 'test_core.c :: core .\n'
        assert sc.command == [
                [DUMMYPATH],
                ]

    def test_failed(self):
        testdict = { 'test_core': 'test_core.c' }
        sc = MockContext(
                [[BUILDPATH, 'test_core', stat.S_IXUSR]],
                [[
                    '[==========] Running 1 test from 1 test case.\n',
                    '[----------] Global test environment set-up.\n',
                    '[----------] 1 test from core\n',
                    '[ RUN      ] core.ok\n',
                    'test_core.cc:12: Failure\n',
                    'Value of: 2\n',
                    'Expected: ok()\n',
                    'Which is: 42\n',
                    '[  FAILED  ] core.ok (0 ms)\n',
                    '[----------] 1 test from core (0 ms total)\n',
                    '\n',
                    '[----------] Global test environment tear-down\n',
                    '[==========] 1 test from 1 test case ran. (0 ms total)\n',
                    '[  PASSED  ] 0 tests.\n',
                    '[  FAILED  ] 1 test, listed below:\n',
                    '[  FAILED  ] core.ok\n',
                    '\n',
                    ' 1 FAILED TEST\n',
                ]]
            )
        e = Executor(sc)
        f = io.StringIO()
        with stdout_redirector(f):
            results = e.test(BUILDPATH, testdict)
        assert len(results) == 1
        assert next(iter(results)).failures() == ['core.ok']
        assert f.getvalue() == 'test_core.c :: core F\n'
        assert sc.command == [
                [DUMMYPATH],
                ]

    def test_filter(self):
        testdict = { 'test_core': 'test_core.c' }
        sc = MockContext(
                [[BUILDPATH, 'test_core', stat.S_IXUSR]],
                [[
                    '[==========] Running 1 test from 1 test case.\n',
                    '[----------] Global test environment set-up.\n',
                    '[----------] 1 test from core\n',
                    '[ RUN      ] core.ok\n',
                    'test_core.cc:12: Failure\n',
                    'Value of: 2\n',
                    'Expected: ok()\n',
                    'Which is: 42\n',
                    '[  FAILED  ] core.ok (0 ms)\n',
                    '[----------] 1 test from core (0 ms total)\n',
                    '\n',
                    '[----------] Global test environment tear-down\n',
                    '[==========] 1 test from 1 test case ran. (0 ms total)\n',
                    '[  PASSED  ] 0 tests.\n',
                    '[  FAILED  ] 1 test, listed below:\n',
                    '[  FAILED  ] core.ok\n',
                    '\n',
                    ' 1 FAILED TEST\n',
                ]]
            )
        e = Executor(sc)
        e.test(BUILDPATH, testdict)
        assert e.test_filter() == { DUMMYPATH: ['core.ok'] }
        e.clear_filter()
        assert e.test_filter() == {}

    def test_failed_filter(self):
        testdict = { 'test_core': 'test_core.c' }
        sc = MockContext(
                [[BUILDPATH, 'test_core', stat.S_IXUSR]],
                [[
                    '[==========] Running 2 tests from 1 test case.\n',
                    '[----------] Global test environment set-up.\n',
                    '[----------] 2 test from core\n',
                    '[ RUN      ] core.test\n',
                    '[       OK ] core.test (0 ms)\n',
                    '[ RUN      ] core.ok\n',
                    'test_core.cc:12: Failure\n',
                    'Value of: 2\n',
                    'Expected: ok()\n',
                    'Which is: 42\n',
                    '[  FAILED  ] core.ok (0 ms)\n',
                    '[----------] 2 tests from core (0 ms total)\n',
                    '\n',
                    '[----------] Global test environment tear-down\n',
                    '[==========] 2 tests from 1 test case ran. (0 ms total)\n',
                    '[  PASSED  ] 1 test.\n',
                    '[  FAILED  ] 1 test, listed below:\n',
                    '[  FAILED  ] core.ok\n',
                    '\n',
                    ' 1 FAILED TEST\n',
                ],
                [
                    '[==========] Running 1 test from 1 test case.\n',
                    '[----------] Global test environment set-up.\n',
                    '[----------] 1 test from core\n',
                    '[ RUN      ] core.ok\n',
                    'test_core.cc:12: Failure\n',
                    'Value of: 2\n',
                    'Expected: ok()\n',
                    'Which is: 42\n',
                    '[  FAILED  ] core.ok (0 ms)\n',
                    '[----------] 1 test from core (0 ms total)\n',
                    '\n',
                    '[----------] Global test environment tear-down\n',
                    '[==========] 1 test from 1 test case ran. (0 ms total)\n',
                    '[  PASSED  ] 0 tests.\n',
                    '[  FAILED  ] 1 test, listed below:\n',
                    '[  FAILED  ] core.ok\n',
                    '\n',
                    ' 1 FAILED TEST\n',
                ]]
            )
        e = Executor(sc)
        e.test(BUILDPATH, testdict)
        assert sc.command == [[DUMMYPATH]]
        e.test(BUILDPATH, testdict)
        assert sc.command == [
                [DUMMYPATH],
                [DUMMYPATH, '--gtest_filter=core.ok'],
                ]

    def test_multiple_failed_filter(self):
        testdict = { 'test_core': 'test_core.c' }
        sc = MockContext(
                [[BUILDPATH, 'test_core', stat.S_IXUSR]],
                [[
                    '[==========] Running 2 tests from 1 test case.\n',
                    '[----------] Global test environment set-up.\n',
                    '[----------] 2 test from core\n',
                    '[ RUN      ] core.test\n',
                    'test_core.cc:12: Failure\n',
                    'Value of: 2\n',
                    'Expected: ok()\n',
                    'Which is: 42\n',
                    '[  FAILED  ] core.test (0 ms)\n',
                    '[ RUN      ] core.ok\n',
                    'test_core.cc:12: Failure\n',
                    'Value of: 2\n',
                    'Expected: ok()\n',
                    'Which is: 42\n',
                    '[  FAILED  ] core.ok (0 ms)\n',
                    '[----------] 2 tests from core (0 ms total)\n',
                    '\n',
                    '[----------] Global test environment tear-down\n',
                    '[==========] 2 tests from 1 test case ran. (0 ms total)\n',
                    '[  PASSED  ] 0 tests.\n',
                    '[  FAILED  ] 2 test, listed below:\n',
                    '[  FAILED  ] core.test\n',
                    '[  FAILED  ] core.ok\n',
                    '\n',
                    ' 2 FAILED TESTS\n',
                ],
                [
                    '[==========] Running 2 tests from 1 test case.\n',
                    '[----------] Global test environment set-up.\n',
                    '[----------] 2 test from core\n',
                    '[ RUN      ] core.test\n',
                    'test_core.cc:12: Failure\n',
                    'Value of: 2\n',
                    'Expected: ok()\n',
                    'Which is: 42\n',
                    '[  FAILED  ] core.test (0 ms)\n',
                    '[ RUN      ] core.ok\n',
                    'test_core.cc:12: Failure\n',
                    'Value of: 2\n',
                    'Expected: ok()\n',
                    'Which is: 42\n',
                    '[  FAILED  ] core.ok (0 ms)\n',
                    '[----------] 2 tests from core (0 ms total)\n',
                    '\n',
                    '[----------] Global test environment tear-down\n',
                    '[==========] 2 tests from 1 test case ran. (0 ms total)\n',
                    '[  PASSED  ] 0 tests.\n',
                    '[  FAILED  ] 2 test, listed below:\n',
                    '[  FAILED  ] core.test\n',
                    '[  FAILED  ] core.ok\n',
                    '\n',
                    ' 2 FAILED TESTS\n',
                ]]
            )
        e = Executor(sc)
        e.test(BUILDPATH, testdict)
        assert sc.command == [[DUMMYPATH]]
        e.test(BUILDPATH, testdict)
        assert sc.command == [
                [DUMMYPATH],
                [DUMMYPATH, '--gtest_filter=core.test:core.ok'],
                ]

    def test_failure_then_success_reruns_all(self):
        testdict = { 'test_core': 'test_core.c' }
        sc = MockContext(
                [[BUILDPATH, 'test_core', stat.S_IXUSR]],
                [[
                    '[==========] Running 1 test from 1 test case.\n',
                    '[----------] Global test environment set-up.\n',
                    '[----------] 1 test from core\n',
                    '[ RUN      ] core.ok\n',
                    'test_core.cc:12: Failure\n',
                    'Value of: 2\n',
                    'Expected: ok()\n',
                    'Which is: 42\n',
                    '[  FAILED  ] core.ok (0 ms)\n',
                    '[----------] 1 test from core (0 ms total)\n',
                    '\n',
                    '[----------] Global test environment tear-down\n',
                    '[==========] 1 test from 1 test case ran. (0 ms total)\n',
                    '[  PASSED  ] 0 tests.\n',
                    '[  FAILED  ] 1 test, listed below:\n',
                    '[  FAILED  ] core.ok\n',
                    '\n',
                    ' 1 FAILED TEST\n',
                ],
                [
                    '[==========] Running 1 test from 1 test case.\n',
                    '[----------] Global test environment set-up.\n',
                    '[----------] 1 test from core\n',
                    '[ RUN      ] core.ok\n',
                    '[       OK ] core.ok (0 ms)\n',
                    '[----------] 1 test from core (0 ms total)\n',
                    '\n',
                    '[----------] Global test environment tear-down\n',
                    '[==========] 1 test from 1 test case ran. (0 ms total)\n',
                    '[  PASSED  ] 1 test.\n',
                ]]
            )
        e = Executor(sc)
        e.test(BUILDPATH, testdict)
        assert sc.command == [[DUMMYPATH]]
        e.test(BUILDPATH, testdict)
        assert sc.command == [
                [DUMMYPATH],
                [DUMMYPATH, '--gtest_filter=core.ok'],
                [DUMMYPATH],
                ]

