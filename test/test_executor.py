#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
test_executor
----------------------------------

Tests for `executor` module.
"""
import os
import re
from testfixtures import TempDirectory

from ttt.executor import Executor
from ttt.executor import GTest
from ttt.executor import BuildFile
from ttt.executor import FileProvider
from ttt.executor import FileSystem
from ttt.watcher import WatchedFile

from ttt.executor import derive_test_files, get_tests, Test, run_test, failing_tests
import stat

from contextlib import contextmanager
import io
import sys

def starts_with_test(filename):
    return filename.startswith('test')

@contextmanager
def stdout_redirector(stream):
    old_stdout = sys.stdout
    sys.stdout = stream
    try:
        yield
    finally:
        sys.stdout = old_stdout

class MockProcess:
    def __init__(self, output):
        self.output = output
        self.command = None

    def streamed_call(self, command, listener):
        self.command = command
        for line in self.output:
            listener(line)

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
        gtest = GTest()
        f = io.StringIO()
        with stdout_redirector(f):
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
        gtest = GTest()
        f = io.StringIO()
        with stdout_redirector(f):
            gtest.execute(MockProcess(results), [])

        assert f.getvalue() == 'core .\n'
        assert gtest.results() == {
                'core': {
                    'core.ok': [],
                    },
                }
        assert gtest.failures() == set()

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
        gtest = GTest()
        f = io.StringIO()
        with stdout_redirector(f):
            gtest.execute(MockProcess(results), [])

        assert f.getvalue() == 'dummy ..\n'
        assert gtest.results() == {
                'dummy': {
                    'dummy.test1': [],
                    'dummy.test2': [],
                    },
                }
        assert gtest.failures() == set()

    def multiple_testcase_success(self):
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
        gtest = GTest()

        f = io.StringIO()
        with stdout_redirector(f):
            gtest.execute(MockProcess(results), [])

        assert f.getvalue() == 'core ....\nblah ..\n'
        assert gtest.results() == {
                'core': {
                    'core.ok': [],
                    'core.okshadow': [],
                    'core.notok': [],
                    'core.blah': [],
                    },
                'blah': {
                    'blah.test1': [],
                    'blah.test2': [],
                    },
                }
        assert gtest.failures() == set()

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
        gtest = GTest()
        f = io.StringIO()
        with stdout_redirector(f):
            gtest.execute(MockProcess(results), [])

        assert f.getvalue() == 'core FF\n'
        assert gtest.results() == {
                'core': {
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
                    },
                }
        assert gtest.failures() == set(['core.ok', 'core.okshadow'])

    def multiple_testcase_failure(self):
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
        gtest = GTest()
        f = io.StringIO()
        with stdout_redirector(f):
            gtest.execute(MockProcess(results), [])

        assert f.getvalue() == 'core .F..\nblah .F\n'
        assert gtest.results() == {
                'core': {
                    'core.ok': [],
                    'core.okshadow': [
                        '/test/test_core.cc:16: Failure\n',
                        'Value of: 2\n',
                        'Expected: ok()\n',
                        'Which is: 42\n',
                        ],
                    'core.notok': [],
                    'core.blah': [],
                    },
                'blah': {
                    'blah.test1': [],
                    'blah.test2': [
                        '/test/test_core.cc:32: Failure\n',
                        'Value of: false\n',
                        '  Actual: false\n',
                        'Expected: true\n',
                        ],
                    },
                }
        assert gtest.failures() == set([ 'core.okshadow', 'dummy.test2' ])

    def test_command_filter_none(self):
        process = MockProcess([])
        gtest = GTest('test/test.c', '/path/to/test')
        f = io.StringIO()
        with stdout_redirector(f):
            gtest.execute(process, [])
        assert process.command == [ '/path/to/test' ]

    def test_command_filter_one(self):
        process = MockProcess([])
        gtest = GTest('test/test.c', '/path/to/test')
        f = io.StringIO()
        with stdout_redirector(f):
            gtest.execute(process, [ 'dummy' ])
        assert process.command == [ '/path/to/test', '--gtest_filter=dummy' ]

    def test_command_filter_many(self):
        process = MockProcess([])
        gtest = GTest('test/test.c', '/path/to/test')
        f = io.StringIO()
        with stdout_redirector(f):
            gtest.execute(process, [ 'dummy1', 'dummy2' ])
        assert process.command == [ '/path/to/test', '--gtest_filter=dummy1:dummy2' ]

class TestExecutor:
    def teardown(self):
        TempDirectory.cleanup_all()

    def test_derive_test_files(self):
        filelist = {
            'dummy.c': WatchedFile(filename='dummy.c', mtime=1),
            'test_dummy.c': WatchedFile(filename='test_dummy.c', mtime=1)
        }
        testfiles = derive_test_files(filelist, 'test_')
        assert testfiles == set(['test_dummy'])

    def test_get_tests(self):
        bf1 = BuildFile('test_dummy', '/path/to/test_dummy', stat.S_IXUSR)
        bf2 = BuildFile('test_dummy.c', '/path/to/test_dummy.c', stat.S_IRUSR)
        filelist = [ bf1, bf2 ]

        class FileSystem(object):
            def walk(self):
                for file in filelist:
                    yield file

            def execute(self, cmd):
                if '/path/to/test_dummy' in cmd:
                    return "\n".join([
                        "Running main() from gtest_main.cc",
                        "dummy.",
                        "  test1",
                        "  test2",
                    ])

        provider = FileProvider(FileSystem())
        testfiles = get_tests(provider, set(['test_dummy']))
        assert testfiles == { '/path/to/test_dummy': Test(
            testgroup='dummy', testcases=['test1', 'test2'],
            abspath='/path/to/test_dummy'
            ) }

    def test_run_test_without_filter(self):
        wd = TempDirectory()
        testfile = wd.write('test_dummy', b'#!/bin/sh\necho "args: $@"')
        os.chmod(testfile, os.stat(testfile).st_mode | stat.S_IXUSR)

        test = Test(
            testgroup='dummy', testcases=['test1', 'test2'],
            abspath=os.path.join(wd.path, 'test_dummy')
            )
        testfilter = []
        results = [ line.strip() for line in run_test(testfile, testfilter) ]
        assert results == [ 'args:' ]

    def test_run_test_with_filter(self):
        wd = TempDirectory()
        testfile = wd.write('test_dummy', b'#!/bin/sh\necho "args: $@"')
        os.chmod(testfile, os.stat(testfile).st_mode | stat.S_IXUSR)

        test = Test(
            testgroup='dummy', testcases=['test1', 'test2'],
            abspath=os.path.join(wd.path, 'test_dummy')
            )
        testfilter = ['dummy.test1']
        results = [ line.strip() for line in run_test(testfile, testfilter) ]
        assert results == [ 'args: --gtest_filter=dummy.test1' ]

    def test_run_test_with_multiple_filters(self):
        wd = TempDirectory()
        testfile = wd.write('test_dummy', b'#!/bin/sh\necho "args: $@"')
        os.chmod(testfile, os.stat(testfile).st_mode | stat.S_IXUSR)

        test = Test(
            testgroup='dummy', testcases=['test1', 'test2'],
            abspath=os.path.join(wd.path, 'test_dummy')
            )
        testfilter = ['dummy.test1', 'dummy.test2']
        results = [ line.strip() for line in run_test(testfile, testfilter) ]
        assert results == [ 'args: --gtest_filter=dummy.test1:dummy.test2' ]

    def test_failing_tests_on_success_results(self):
        test = Test(testgroup='dummy', testcases=['test1', 'test2'], abspath='/path/to/test_dummy')
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
        test_filter = failing_tests(results, test)
        assert test_filter == []

    def test_failing_tests_on_failure_results(self):
        test = Test(testgroup='dummy', testcases=['test1', 'test2'], abspath='/path/to/test_dummy')
        results = [
'Running main() from gtest_main.cc\n',
'[==========] Running 2 tests from 1 test case.\n',
'[----------] Global test environment set-up.\n',
'[----------] 2 tests from dummy\n',
'[ RUN      ] dummy.test1\n',
'[       OK ] dummy.test1 (0 ms)\n',
'[ RUN      ] dummy.test2\n',
'/path/to/test_dummy.cc:16: Failure\n',
'Value of: 2\n',
'Expected: ok()\n',
'Which is: 42\n',
'[  FAILED  ] dummy.test2 (0 ms)\n',
'[----------] 2 tests from dummy (0 ms total)\n',
'\n',
'[----------] Global test environment tear-down\n',
'[==========] 2 tests from 1 test case ran. (0 ms total)\n',
'[  PASSED  ] 1 tests.\n',
'[  FAILED  ] 1 test, listed below:\n',
'[  FAILED  ] dummy.test1\n',
'\n',
' 1 FAILED TEST\n',
                ]
        test_filter = failing_tests(results, test)
        assert test_filter == [ 'dummy.test1' ]

    def test_failing_tests_on_multiple_failure_results(self):
        test = Test(testgroup='dummy', testcases=['test1', 'test2'], abspath='/path/to/test_dummy')
        results = [
'Running main() from gtest_main.cc\n',
'[==========] Running 2 tests from 1 test case.\n',
'[----------] Global test environment set-up.\n',
'[----------] 2 tests from dummy\n',
'[ RUN      ] dummy.test1\n',
'/path/to/test_dummy.cc:12: Failure\n',
'Value of: 2\n',
'Expected: ok()\n',
'Which is: 42\n',
'[  FAILED  ] dummy.test1 (0 ms)\n',
'[ RUN      ] dummy.test2\n',
'/path/to/test_dummy.cc:16: Failure\n',
'Value of: 2\n',
'Expected: ok()\n',
'Which is: 42\n',
'[  FAILED  ] dummy.test2 (0 ms)\n',
'[----------] 2 tests from dummy (0 ms total)\n',
'\n',
'[----------] Global test environment tear-down\n',
'[==========] 2 tests from 1 test case ran. (0 ms total)\n',
'[  PASSED  ] 0 tests.\n',
'[  FAILED  ] 2 tests, listed below:\n',
'[  FAILED  ] dummy.test1\n',
'[  FAILED  ] dummy.test2\n',
'\n',
' 2 FAILED TESTS\n',
                ]
        test_filter = failing_tests(results, test)
        assert test_filter == [ 'dummy.test1', 'dummy.test2' ]


class TestFileSystem:
    def setup(self):
        pass

    def teardown(self):
        TempDirectory.cleanup_all()

    def test_file_system(self):
        wd = TempDirectory()
        wd.write('test1.txt', b'')
        wd.write('test2.txt', b'')
        wd.makedir('test');
        wd.write(['test', 'test3.txt'], b'')
        fs = FileSystem(wd.path)

        assert [ f.name() for f in fs.walk() ] == [ 'test1.txt', 'test2.txt', 'test3.txt' ]

class TestProvider:
    def test_provider(self):
        bf1 = BuildFile('test_dummy', '/path/to/test_dummy', stat.S_IXUSR)
        bf2 = BuildFile('dummy.c', '/path/to/dummy.c', stat.S_IRUSR)
        bf3 = BuildFile('test_dummy.c', '/path/to/test_dummy.c', stat.S_IRUSR)
        filelist = [ bf1, bf2, bf3 ]

        class FileSystem(object):
            def walk(self):
                for file in filelist:
                    yield file

        fs = FileSystem()
        provider = FileProvider(fs)
        t = [ f for f in provider.glob_files(starts_with_test) ]

        assert t == [ bf1, bf3 ]

# class TestExecutor:
#     def test_executor(self):
#         bf1 = BuildFile('test_dummy', '/path/to/test_dummy', stat.S_IXUSR)
#         bf2 = BuildFile('dummy.c', '/path/to/dummy.c', stat.S_IRUSR)
#         bf3 = BuildFile('test_dummy.c', '/path/to/test_dummy.c', stat.S_IRUSR)
#
#         fs = MockFileSystem([ bf1, bf2, bf3 ])
#         provider = FileProvider(fs)
#         e = Executor(provider)
#
#         filelist = {
#             'dummy.c': TestFile(prefix='test_', testname='dummy', filename='test_dummy')
#         }
#         assert e.test(filelist) == []

