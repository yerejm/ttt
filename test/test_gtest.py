#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
test_gtest
----------------------------------

Tests for `gtest` module.
"""

import os

import pytest

from ttt.gtest import GTest

class MockTerminal:
    def __init__(self):
        self.output = ''

    def write(self, string):
        self.output += string

    def writeln(self, string=''):
        self.write(string + os.linesep)

    def getvalue(self):
        return self.output

class MockProcess:
    def __init__(self, output):
        self.output = output
        self.command = None

    def streamed_call(self, command, listener):
        self.command = command
        for line in self.output:
            listener(line)
        return (0, self.output)

class TestGTest:
    def test_run_time(self):
        results = [
'Running main() from gtest_main.cc\n',
'[==========] Running 2 tests from 1 test case.\n',
'[----------] Global test environment set-up.\n',
'[----------] 2 tests from dummy\n',
'[ RUN      ] dummy.test1\n',
'[       OK ] dummy.test1 (0 ms)\n',
'[ RUN      ] dummy.test2\n',
'[       OK ] dummy.test2 (0 ms)\n',
'[----------] 2 tests from dummy (0 ms total)\n',
'\n',
'[----------] Global test environment tear-down\n',
'[==========] 2 tests from 1 test case ran. (3 ms total)\n',
'[  PASSED  ] 2 tests.\n'
                ]
        f = MockTerminal()
        gtest = GTest('/test/test_core.cc', term=f)
        gtest.execute(MockProcess(results), [])

        assert gtest.run_time() == 3

    def test_one_testcase_one_success(self):
        results = [
'Running main() from gtest_main.cc\n',
'Note: Google Test filter = core.ok\n',
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
                ]
        f = MockTerminal()
        gtest = GTest('/test/test_core.cc', term=f)
        gtest.execute(MockProcess(results), [])

        assert f.getvalue() == '/test/test_core.cc :: core .' + os.linesep
        assert gtest.results() == { 'core.ok': [], }
        assert gtest.failures() == []
        assert gtest.fails() == 0
        assert gtest.passes() == 1

    def test_one_testcase_success(self):
        results = [
'Running main() from gtest_main.cc\n',
'[==========] Running 2 tests from 1 test case.\n',
'[----------] Global test environment set-up.\n',
'[----------] 2 tests from dummy\n',
'[ RUN      ] dummy.test1\n',
'[       OK ] dummy.test1 (0 ms)\n',
'[ RUN      ] dummy.test2\n',
'[       OK ] dummy.test2 (0 ms)\n',
'[----------] 2 tests from dummy (0 ms total)\n',
'\n',
'[----------] Global test environment tear-down\n',
'[==========] 2 tests from 1 test case ran. (0 ms total)\n',
'[  PASSED  ] 2 tests.\n'
                ]
        f = MockTerminal()
        gtest = GTest('/test/test_core.cc', term=f)
        gtest.execute(MockProcess(results), [])

        assert f.getvalue() == '/test/test_core.cc :: dummy ..' + os.linesep
        assert gtest.results() == { 'dummy.test1': [], 'dummy.test2': [], }
        assert gtest.failures() == []
        assert gtest.fails() == 0
        assert gtest.passes() == 2

    def test_multiple_testcase_success(self):
        results = [
'Running main() from gtest_main.cc\n',
'[==========] Running 6 tests from 2 test cases.\n',
'[----------] Global test environment set-up.\n',
'[----------] 4 tests from core\n',
'[ RUN      ] core.ok\n',
'[       OK ] core.ok (0 ms)\n',
'[ RUN      ] core.okshadow\n',
'[       OK ] core.okshadow (0 ms)\n',
'[ RUN      ] core.notok\n',
'[       OK ] core.notok (0 ms)\n',
'[ RUN      ] core.blah\n',
'[       OK ] core.blah (0 ms)\n',
'[----------] 4 tests from core (0 ms total)\n',
'\n',
'[----------] 2 tests from blah\n',
'[ RUN      ] blah.test1\n',
'[       OK ] blah.test1 (0 ms)\n',
'[ RUN      ] blah.test2\n',
'[       OK ] blah.test2 (0 ms)\n',
'[----------] 2 tests from blah (0 ms total)\n',
'\n',
'[----------] Global test environment tear-down\n',
'[==========] 6 tests from 2 test cases ran. (0 ms total)\n',
'[  PASSED  ] 6 tests.\n',
                ]
        f = MockTerminal()
        gtest = GTest('/test/test_core.cc', term=f)
        gtest.execute(MockProcess(results), [])

        assert f.getvalue() == os.linesep.join([
            '/test/test_core.cc :: core ....',
            '/test/test_core.cc :: blah ..'
            ]) + os.linesep
        assert gtest.results() == {
                'core.ok': [],
                'core.okshadow': [],
                'core.notok': [],
                'core.blah': [],
                'blah.test1': [],
                'blah.test2': [],
            }
        assert gtest.failures() == []
        assert gtest.fails() == 0
        assert gtest.passes() == 6

    def test_one_testcase_failure(self):
        results = [
'Running main() from gtest_main.cc\n',
'Note: Google Test filter = core.ok:core.ok:core.okshadow\n',
'[==========] Running 2 tests from 1 test case.\n',
'[----------] Global test environment set-up.\n',
'[----------] 2 tests from core\n',
'[ RUN      ] core.ok\n',
'/test/test_core.cc:12: Failure\n',
'Value of: 2\n',
'Expected: ok()\n',
'Which is: 42\n',
'[  FAILED  ] core.ok (0 ms)\n',
'[ RUN      ] core.okshadow\n',
'/test/test_core.cc:16: Failure\n',
'Value of: 1\n',
'Expected: ok()\n',
'Which is: 42\n',
'[  FAILED  ] core.okshadow (0 ms)\n',
'[----------] 2 tests from core (0 ms total)\n',
'\n',
'[----------] Global test environment tear-down\n',
'[==========] 2 tests from 1 test case ran. (0 ms total)\n',
'[  PASSED  ] 0 tests.\n',
'[  FAILED  ] 2 tests, listed below:\n',
'[  FAILED  ] core.ok\n',
'[  FAILED  ] core.okshadow\n',
'\n',
' 2 FAILED TESTS\n',
                ]
        f = MockTerminal()
        gtest = GTest('/test/test_core.cc', term=f)
        gtest.execute(MockProcess(results), [])

        assert f.getvalue() == '/test/test_core.cc :: core FF' + os.linesep
        assert gtest.results() == {
                'core.ok': [
                    '/test/test_core.cc:12: Failure',
                    'Value of: 2',
                    'Expected: ok()',
                    'Which is: 42',
                    ],
                'core.okshadow': [
                    '/test/test_core.cc:16: Failure',
                    'Value of: 1',
                    'Expected: ok()',
                    'Which is: 42',
                    ],
            }
        assert gtest.failures() == ['core.ok', 'core.okshadow']
        assert gtest.fails() == 2
        assert gtest.passes() == 0

    def test_multiple_testcase_failure(self):
        results = [
'Running main() from gtest_main.cc\n',
'[==========] Running 6 tests from 2 test cases.\n',
'[----------] Global test environment set-up.\n',
'[----------] 4 tests from core\n',
'[ RUN      ] core.ok\n',
'[       OK ] core.ok (0 ms)\n',
'[ RUN      ] core.okshadow\n',
'/test/test_core.cc:16: Failure\n',
'Value of: 2\n',
'Expected: ok()\n',
'Which is: 42\n',
'[  FAILED  ] core.okshadow (0 ms)\n',
'[ RUN      ] core.notok\n',
'[       OK ] core.notok (0 ms)\n',
'[ RUN      ] core.blah\n',
'[       OK ] core.blah (0 ms)\n',
'[----------] 4 tests from core (0 ms total)\n',
'\n',
'[----------] 2 tests from blah\n',
'[ RUN      ] blah.test1\n',
'[       OK ] blah.test1 (0 ms)\n',
'[ RUN      ] blah.test2\n',
'/test/test_core.cc:32: Failure\n',
'Value of: false\n',
'  Actual: false\n',
'Expected: true\n',
'[  FAILED  ] blah.test2 (0 ms)\n',
'[----------] 2 tests from blah (0 ms total)\n',
'\n',
'[----------] Global test environment tear-down\n',
'[==========] 6 tests from 2 test cases ran. (1 ms total)\n',
'[  PASSED  ] 4 tests.\n',
'[  FAILED  ] 2 tests, listed below:\n',
'[  FAILED  ] core.okshadow\n',
'[  FAILED  ] blah.test2\n',
                ]
        f = MockTerminal()
        gtest = GTest('/test/test_core.cc', term=f)
        gtest.execute(MockProcess(results), [])

        assert f.getvalue() == os.linesep.join([
            '/test/test_core.cc :: core .F..',
            '/test/test_core.cc :: blah .F'
            ]) + os.linesep
        assert gtest.results() == {
                'core.ok': [],
                'core.okshadow': [
                    '/test/test_core.cc:16: Failure',
                    'Value of: 2',
                    'Expected: ok()',
                    'Which is: 42',
                    ],
                'core.notok': [],
                'core.blah': [],
                'blah.test1': [],
                'blah.test2': [
                    '/test/test_core.cc:32: Failure',
                    'Value of: false',
                    'Actual: false',
                    'Expected: true',
                    ],
            }
        assert gtest.failures() == [ 'core.okshadow', 'blah.test2' ]
        assert gtest.fails() == 2
        assert gtest.passes() == 4

    def test_command_filter_none(self):
        process = MockProcess([])
        gtest = GTest('/test/test_core.cc', '/path/to/test')
        gtest.execute(process, [])
        assert process.command == [ '/path/to/test' ]

    def test_command_filter_one(self):
        process = MockProcess([])
        gtest = GTest('/test/test_core.cc', '/path/to/test')
        gtest.execute(process, [ 'dummy' ])
        assert process.command == [ '/path/to/test', '--gtest_filter=dummy' ]

    def test_command_filter_many(self):
        process = MockProcess([])
        gtest = GTest('/test/test_core.cc', '/path/to/test')
        gtest.execute(process, [ 'dummy1', 'dummy2' ])
        assert process.command == [ '/path/to/test', '--gtest_filter=dummy1:dummy2' ]

    def test_corrupt_test_output_missing_testcase(self):
        f = MockTerminal()
        gtest = GTest('/test/test_core.cc', term=f)

        with pytest.raises(Exception):
            gtest.end_test('')

        gtest._testcase = ''

        with pytest.raises(Exception):
            gtest.end_test('')

        gtest._test = ''

        gtest.end_test('')

        assert f.getvalue() == '.'

    def test_path_stripping(self):
        results = [
'Running main() from gtest_main.cc\n',
'Note: Google Test filter = core.ok:core.ok:core.okshadow\n',
'[==========] Running 1 test from 1 test case.\n',
'[----------] Global test environment set-up.\n',
'[----------] 1 tests from core\n',
'[ RUN      ] core.ok\n',
'/path/test/test_core.cc:12: Failure\n',
'Value of: 2\n',
'Expected: ok()\n',
'Which is: 42\n',
'[  FAILED  ] core.ok (0 ms)\n',
'[----------] 1 tests from core (0 ms total)\n',
'\n',
'[----------] Global test environment tear-down\n',
'[==========] 1 test from 1 test case ran. (0 ms total)\n',
'[  PASSED  ] 0 tests.\n',
'[  FAILED  ] 1 test, listed below:\n',
'[  FAILED  ] core.ok\n',
'\n',
' 1 FAILED TESTS\n',
                ]
        f = MockTerminal()
        gtest = GTest('test/test_core.cc', term=f)
        gtest.execute(MockProcess(results), [])
        assert gtest.results() == {
                'core.ok': [
                    'test/test_core.cc:12: Failure',
                    'Value of: 2',
                    'Expected: ok()',
                    'Which is: 42',
                    ],
            }

