from __future__ import unicode_literals
import os
import collections
import subprocess
import re
import termstyle
import colorama
import platform
import stat
import sys

from ttt import subproc

if sys.version_info < (3,):
    text_type = unicode
    binary_type = str
else:
    text_type = str
    binary_type = bytes

def stdout_write(string):
    sys.stdout.write(text_type(string))

class GTest(object):
    WAITING_TESTCASE, WAITING_TEST, IN_TEST = range(3)
    TESTCASE_START_RE = re.compile('^\[----------\] \d+ tests? from (.*?)$')
    TESTCASE_END_RE   = re.compile('^\[----------\] \d+ tests? from (.*?) \(\d+ ms total\)$')
    TEST_START_RE     = re.compile('^\[ RUN      \] (.*?)$')
    TEST_END_RE       = re.compile('^\[  (FAILED |     OK) \] (.*?)$')
    TESTCASE_TIME_RE  = re.compile('^\[==========\] \d tests? from \d test cases? ran. \((\d+) ms total\)$')

    def __init__(self, source=None, executable=None):
        self._source = source
        self._executable = executable
        self._output = []
        self._tests = collections.defaultdict(dict)
        self._state = GTest.WAITING_TESTCASE
        self._testcase = None
        self._test = None
        self._elapsed = 0

    def executable(self):
        return self._executable

    def run_time(self):
        return self._elapsed

    def execute(self, provider, test_filters):
        command = [ self._executable ]
        if test_filters:
            command.append("--gtest_filter={}".format(':'.join(test_filters)))
        provider.streamed_call(command, self)

    def __call__(self, line):
        def testcase_starts_at(line):
            return GTest.TESTCASE_START_RE.match(line)
        def testcase_ends_at(line):
            return GTest.TESTCASE_END_RE.match(line)
        def test_starts_at(line):
            return GTest.TEST_START_RE.match(line)
        def test_ends_at(line):
            return GTest.TEST_END_RE.match(line)
        def test_elapsed_at(line):
            return GTest.TESTCASE_TIME_RE.match(line)

        line = line.strip()
        if self._state == GTest.IN_TEST:
            self._output.append(line)

        if self._state == GTest.WAITING_TESTCASE and testcase_starts_at(line):
            self.begin_testcase(line)
            self._state = GTest.WAITING_TEST
        elif self._state == GTest.WAITING_TEST and testcase_ends_at(line):
            self.end_testcase(line)
            self._state = GTest.WAITING_TESTCASE
        elif self._state == GTest.WAITING_TEST and test_starts_at(line):
            self.begin_test(line)
            self._state = GTest.IN_TEST
        elif self._state == GTest.IN_TEST and test_ends_at(line):
            self.end_test(line)
            self._state = GTest.WAITING_TEST
        elif self._state == GTest.WAITING_TESTCASE:
            match = test_elapsed_at(line)
            if match:
                self._elapsed = int(match.group(1))
        return None

    def begin_testcase(self, line):
        testcase = line[line.rfind(' ') + 1:]
        self._testcase = testcase

        if self._source is not None:
            stdout_write(self._source)
            stdout_write(' :: ')
        stdout_write(testcase)
        stdout_write(' ')

    def end_testcase(self, line):
        self._testcase = None

        stdout_write('\n')

    def begin_test(self, line):
        test = line[line.rfind(' ') + 1:]
        self._test = test
        self._output = []

    def end_test(self, line):
        if self._testcase is None:
            raise Exception('Invalid current testcase')
        if self._test is None:
            raise Exception('Invalid current test')
        self._tests[self._testcase][self._test] = self._output[:-1]
        self._current_test = None

        stdout_write('F' if '[  FAILED  ]' in line else '.')

    def results(self):
        return self._tests

    def failures(self):
        failures = set()
        for tests in self._tests.values():
            for test, results in tests.items():
                if results:
                    failures.add(test)
        return failures

Test = collections.namedtuple(
    "Test",
    [ "testgroup", "testcases", "abspath" ]
)
Test.__new__.__defaults__ = (None, None, None)

class Executor(object):
    def __init__(self, build_path):
        self.test_filter = {}
        self.provider = FileProvider(FileSystem(build_path))

    def test(self, filelist):
        test_filter = self.test_filter
        testfiles = derive_test_files(filelist, 'test_')
        testlist = create_tests(self.provider, testfiles)

        if test_filter:
            test_filter = self.run_tests(testlist, test_filter)
        if test_filter:
            self.test_filter = test_filter
            return test_filter
        test_filter = self.run_tests(testlist, set())
        self.test_filter = test_filter
        return test_filter

    def run_tests(self, testlist, test_filter):
        for test in testlist:
            if not test_filter or test.executable() in test_filter:
                test.execute(self.provider, test_filter[test.executable()] if test_filter else [])
                failures = test.failures()
                if failures:
                    return { test.executable(): failures }
        return {}

def create_test(provider, path):
    lines = provider.execute([path, '--gtest_list_tests'])
    testgroup = lines[1][0:-1]
    testcases = [ case.strip() for case in lines[2:] ]
    print("{} -> {}".format(testgroup, testcases))
    return Test(abspath=path, testgroup=testgroup, testcases=testcases)

def create_tests(provider, testfiles):
    tests = []
    for buildfile in provider.glob_files(lambda x: x in testfiles):
        if buildfile.is_executable_file():
            filepath = buildfile.path()
            tests.append(GTest(filepath))
    return tests

def get_tests(provider, testfiles):
    tests = {}
    for buildfile in provider.glob_files(lambda x: x in testfiles):
        if buildfile.is_executable_file():
            filepath = buildfile.path()
            tests[filepath] = create_test(provider, filepath)
    return tests

def exe_suffix():
    return ".exe" if platform.system() == 'Windows' else ""

def derive_test_files(source_files, test_prefix):
    """ Derive from source files a set of the associated build files """
    testfiles = set()
    for filepath, watchedfile in source_files.items():
        filename = watchedfile.filename
        if filename.startswith(test_prefix):
            testfiles.add(filename[:filename.rfind('.')] + exe_suffix())
    return testfiles

def run_test(test, test_filter):
    test_results = []
    def fails(line):
        test_results.append(line)
        colorer = termstyle.red if 'FAILED' in line else termstyle.green
        brightness = colorama.Style.BRIGHT if platform.system() == 'Windows' else colorama.Style.NORMAL
        if line[:1] == '[':
            return '{}{}{}{}'.format(brightness, colorer(line[:13]), termstyle.reset, line[13:])

    command = [test]
    # command.append('--gtest_color=yes')
    if test_filter:
        command.append("--gtest_filter={}".format(':'.join(test_filter)))
    print("Run {}".format(command))
    subproc.call_output(command, universal_newlines=True, line_handler=fails)
    return test_results

def failing_tests(test_results, test_details):
    failed = []
    testgroup = test_details.testgroup
    tests = set([ '{}.{}'.format(testgroup, test) for test in test_details.testcases ])
    for line in test_results[::-1]:
        if "==========" in line:
            break;
            # print("search: {} in {}".format(pattern.testname, line))
        for test in tests:
            if test in line and "FAILED" in line:
                failed.append(test)
    return failed[::-1]

class BuildFile(object):
    def __init__(self, name, path, statmode):
        self._name = name
        self._path = path
        self._statmode = statmode

    def name(self):
        return self._name

    def path(self):
        return self._path

    def is_executable_file(self):
        return self._statmode & stat.S_IXUSR

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def __hash__(self):
        return hash(tuple(self.__dict__.values()))

    def __str__(self):
        return self.name()

    def __repr__(self):
        return "BuildFile({}, {}, {})".format(
                repr(self.name()),
                repr(self.path()),
                self._statmode
            )

class FileSystem(object):
    def __init__(self, root_directory):
        self.root_directory = root_directory

    def walk(self):
        try:
            from os import scandir, walk
        except ImportError:
            from scandir import scandir, walk
        for dirpath, _, filelist in walk(self.root_directory):
            for filename in filelist:
                path = os.path.join(dirpath, filename)
                statmode = os.stat(path).st_mode
                if stat.S_ISREG(statmode):
                    yield BuildFile(filename, path, statmode)
    def execute(self, cmd):
        return subprocess.check_output(cmd, universal_newlines=True)

class FileProvider(object):
    def __init__(self, file_system):
        self.file_system = file_system

    def glob_files(self, selector):
        for file in self.file_system.walk():
            if selector(file.name()):
                yield file

    def execute(self, cmd):
        return self.file_system.execute(cmd).splitlines()

    def streamed_call(self, command, listener):
        return subproc.call_output(command, universal_newlines=True, line_handler=listener)

