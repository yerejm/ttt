#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
test_executor
----------------------------------

Tests for `executor` module.
"""
import os
import sys
import stat

from testfixtures import TempDirectory

from ttt.executor import Executor
from ttt.systemcontext import SystemContext
from ttt.terminal import Terminal

class MockContext(SystemContext):
    def __init__(self, results=[]):
        super(MockContext, self).__init__()
        self.results = results[::-1]
        self.command = []
        self.output = ''

    def streamed_call(self, command, listener):
        self.command.append(command)
        if self.results:
            results = self.results.pop()
            for line in results:
                listener(sys.stdout, line)
            return (0, results, [])
        return (0, [], [])

class MockTerminal(Terminal):
    def __init__(self):
        super(MockTerminal, self).__init__()
        self.output = ''

    def getvalue(self):
        return self.output

    def write(self, string):
        self.output += string

BUILDPATH = os.path.sep + os.path.join('path', 'to', 'build')
DUMMYPATH = os.path.join(BUILDPATH, 'test_core')

class TestExecutor:
    def test_passed(self):
        testdict = [ ('test_core.cc', DUMMYPATH) ]
        sc = MockContext(
                [[
                    '[==========] Running 1 test from 1 test case.',
                    '[----------] Global test environment set-up.',
                    '[----------] 1 test from core',
                    '[ RUN      ] core.ok',
                    '[       OK ] core.ok (0 ms)',
                    '[----------] 1 test from core (1 ms total)',
                    '',
                    '[----------] Global test environment tear-down',
                    '[==========] 1 test from 1 test case ran. (1 ms total)',
                    '[  PASSED  ] 1 test.',
                ]]
            )
        t = MockTerminal()
        e = Executor(sc, t)
        results = e.test(testdict)
        assert results == {
                'total_runtime': 0.001,
                'total_passed': 1,
                'total_failed': 0,
                'failures': []
                }
        assert t.getvalue() == 'test_core.cc :: core .' + os.linesep
        assert sc.command == [
                [DUMMYPATH],
                ]

    def test_failed(self):
        testdict = [ ('test_core.cc', DUMMYPATH) ]
        sc = MockContext(
                [[
                    '[==========] Running 1 test from 1 test case.',
                    '[----------] Global test environment set-up.',
                    '[----------] 1 test from core',
                    '[ RUN      ] core.ok',
                    'test_core.cc:12: Failure',
                    'Value of: 2',
                    'Expected: ok()',
                    'Which is: 42',
                    '[  FAILED  ] core.ok (0 ms)',
                    '[----------] 1 test from core (1 ms total)',
                    '',
                    '[----------] Global test environment tear-down',
                    '[==========] 1 test from 1 test case ran. (1 ms total)',
                    '[  PASSED  ] 0 tests.',
                    '[  FAILED  ] 1 test, listed below:',
                    '[  FAILED  ] core.ok',
                    '',
                    ' 1 FAILED TEST',
                ]]
            )
        t = MockTerminal()
        e = Executor(sc, t)
        results = e.test(testdict)
        assert results == {
                'total_runtime': 0.001,
                'total_passed': 0,
                'total_failed': 1,
                'failures': [[
                        'core.ok',
                        [
                            'test_core.cc:12: Failure',
                            'Value of: 2',
                            'Expected: ok()',
                            'Which is: 42',
                        ],
                        []
                    ]]
                }
        assert t.getvalue() == 'test_core.cc :: core F' + os.linesep
        assert sc.command == [
                [DUMMYPATH],
                ]

    def test_mixed_results(self):
        testdict = [ ('test_core.cc', DUMMYPATH) ]
        sc = MockContext(
                [[
                    '[==========] Running 2 tests from 1 test case.',
                    '[----------] Global test environment set-up.',
                    '[----------] 2 test from core',
                    '[ RUN      ] core.test',
                    '[       OK ] core.test (0 ms)',
                    '[ RUN      ] core.ok',
                    'test_core.cc:12: Failure',
                    'Value of: 2',
                    'Expected: ok()',
                    'Which is: 42',
                    '[  FAILED  ] core.ok (0 ms)',
                    '[----------] 2 tests from core (1 ms total)',
                    '',
                    '[----------] Global test environment tear-down',
                    '[==========] 2 tests from 1 test case ran. (1 ms total)',
                    '[  PASSED  ] 1 test.',
                    '[  FAILED  ] 1 test, listed below:',
                    '[  FAILED  ] core.ok',
                    '',
                    ' 1 FAILED TEST',
                ]]
            )
        t = MockTerminal()
        e = Executor(sc, t)
        results = e.test(testdict)
        assert results == {
                'total_runtime': 0.001,
                'total_passed': 1,
                'total_failed': 1,
                'failures': [[
                        'core.ok',
                        [
                            'test_core.cc:12: Failure',
                            'Value of: 2',
                            'Expected: ok()',
                            'Which is: 42',
                        ],
                        []
                    ]]
                }
        assert t.getvalue() == 'test_core.cc :: core .F' + os.linesep
        assert sc.command == [
                [DUMMYPATH],
                ]

    def test_filter(self):
        testdict = [ ('test_core.cc', DUMMYPATH) ]
        sc = MockContext(
                [[
                    '[==========] Running 1 test from 1 test case.',
                    '[----------] Global test environment set-up.',
                    '[----------] 1 test from core',
                    '[ RUN      ] core.ok',
                    'test_core.cc:12: Failure',
                    'Value of: 2',
                    'Expected: ok()',
                    'Which is: 42',
                    '[  FAILED  ] core.ok (0 ms)',
                    '[----------] 1 test from core (0 ms total)',
                    '',
                    '[----------] Global test environment tear-down',
                    '[==========] 1 test from 1 test case ran. (0 ms total)',
                    '[  PASSED  ] 0 tests.',
                    '[  FAILED  ] 1 test, listed below:',
                    '[  FAILED  ] core.ok',
                    '',
                    ' 1 FAILED TEST',
                ]]
            )
        e = Executor(sc)
        e.test(testdict)
        assert e.test_filter() == { DUMMYPATH: ['core.ok'] }
        e.clear_filter()
        assert e.test_filter() == {}

    def test_failed_filter(self):
        testdict = [ ('test_core.cc', DUMMYPATH) ]
        sc = MockContext(
                [[
                    '[==========] Running 2 tests from 1 test case.',
                    '[----------] Global test environment set-up.',
                    '[----------] 2 test from core',
                    '[ RUN      ] core.test',
                    '[       OK ] core.test (0 ms)',
                    '[ RUN      ] core.ok',
                    'test_core.cc:12: Failure',
                    'Value of: 2',
                    'Expected: ok()',
                    'Which is: 42',
                    '[  FAILED  ] core.ok (0 ms)',
                    '[----------] 2 tests from core (0 ms total)',
                    '',
                    '[----------] Global test environment tear-down',
                    '[==========] 2 tests from 1 test case ran. (0 ms total)',
                    '[  PASSED  ] 1 test.',
                    '[  FAILED  ] 1 test, listed below:',
                    '[  FAILED  ] core.ok',
                    '',
                    ' 1 FAILED TEST',
                ],
                [
                    '[==========] Running 1 test from 1 test case.',
                    '[----------] Global test environment set-up.',
                    '[----------] 1 test from core',
                    '[ RUN      ] core.ok',
                    'test_core.cc:12: Failure',
                    'Value of: 2',
                    'Expected: ok()',
                    'Which is: 42',
                    '[  FAILED  ] core.ok (0 ms)',
                    '[----------] 1 test from core (0 ms total)',
                    '',
                    '[----------] Global test environment tear-down',
                    '[==========] 1 test from 1 test case ran. (0 ms total)',
                    '[  PASSED  ] 0 tests.',
                    '[  FAILED  ] 1 test, listed below:',
                    '[  FAILED  ] core.ok',
                    '',
                    ' 1 FAILED TEST',
                ]]
            )
        e = Executor(sc)
        e.test(testdict)
        assert sc.command == [[DUMMYPATH]]
        e.test(testdict)
        assert sc.command == [
                [DUMMYPATH],
                [DUMMYPATH, '--gtest_filter=core.ok'],
                ]

    def test_multiple_failed_filter(self):
        testdict = [ ('test_core.cc', DUMMYPATH) ]
        sc = MockContext(
                [[
                    '[==========] Running 2 tests from 1 test case.',
                    '[----------] Global test environment set-up.',
                    '[----------] 2 test from core',
                    '[ RUN      ] core.test',
                    'test_core.cc:12: Failure',
                    'Value of: 2',
                    'Expected: ok()',
                    'Which is: 42',
                    '[  FAILED  ] core.test (0 ms)',
                    '[ RUN      ] core.ok',
                    'test_core.cc:12: Failure',
                    'Value of: 2',
                    'Expected: ok()',
                    'Which is: 42',
                    '[  FAILED  ] core.ok (0 ms)',
                    '[----------] 2 tests from core (0 ms total)',
                    '',
                    '[----------] Global test environment tear-down',
                    '[==========] 2 tests from 1 test case ran. (0 ms total)',
                    '[  PASSED  ] 0 tests.',
                    '[  FAILED  ] 2 test, listed below:',
                    '[  FAILED  ] core.test',
                    '[  FAILED  ] core.ok',
                    '',
                    ' 2 FAILED TESTS',
                ],
                [
                    '[==========] Running 2 tests from 1 test case.',
                    '[----------] Global test environment set-up.',
                    '[----------] 2 test from core',
                    '[ RUN      ] core.test',
                    'test_core.cc:12: Failure',
                    'Value of: 2',
                    'Expected: ok()',
                    'Which is: 42',
                    '[  FAILED  ] core.test (0 ms)',
                    '[ RUN      ] core.ok',
                    'test_core.cc:12: Failure',
                    'Value of: 2',
                    'Expected: ok()',
                    'Which is: 42',
                    '[  FAILED  ] core.ok (0 ms)',
                    '[----------] 2 tests from core (0 ms total)',
                    '',
                    '[----------] Global test environment tear-down',
                    '[==========] 2 tests from 1 test case ran. (0 ms total)',
                    '[  PASSED  ] 0 tests.',
                    '[  FAILED  ] 2 test, listed below:',
                    '[  FAILED  ] core.test',
                    '[  FAILED  ] core.ok',
                    '',
                    ' 2 FAILED TESTS',
                ]]
            )
        e = Executor(sc)
        e.test(testdict)
        assert sc.command == [[DUMMYPATH]]
        e.test(testdict)
        assert sc.command == [
                [DUMMYPATH],
                [DUMMYPATH, '--gtest_filter=core.test:core.ok'],
                ]

    def test_failure_then_success_reruns_all(self):
        testdict = [ ('test_core.cc', DUMMYPATH) ]
        sc = MockContext(
                [[
                    '[==========] Running 1 test from 1 test case.',
                    '[----------] Global test environment set-up.',
                    '[----------] 1 test from core',
                    '[ RUN      ] core.ok',
                    'test_core.cc:12: Failure',
                    'Value of: 2',
                    'Expected: ok()',
                    'Which is: 42',
                    '[  FAILED  ] core.ok (0 ms)',
                    '[----------] 1 test from core (0 ms total)',
                    '',
                    '[----------] Global test environment tear-down',
                    '[==========] 1 test from 1 test case ran. (0 ms total)',
                    '[  PASSED  ] 0 tests.',
                    '[  FAILED  ] 1 test, listed below:',
                    '[  FAILED  ] core.ok',
                    '',
                    ' 1 FAILED TEST',
                ],
                [
                    '[==========] Running 1 test from 1 test case.',
                    '[----------] Global test environment set-up.',
                    '[----------] 1 test from core',
                    '[ RUN      ] core.ok',
                    '[       OK ] core.ok (0 ms)',
                    '[----------] 1 test from core (0 ms total)',
                    '',
                    '[----------] Global test environment tear-down',
                    '[==========] 1 test from 1 test case ran. (0 ms total)',
                    '[  PASSED  ] 1 test.',
                ]]
            )
        e = Executor(sc)
        e.test(testdict)
        assert sc.command == [[DUMMYPATH]]
        e.test(testdict)
        assert sc.command == [
                [DUMMYPATH],
                [DUMMYPATH, '--gtest_filter=core.ok'],
                ]

