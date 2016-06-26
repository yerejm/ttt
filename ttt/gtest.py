"""
ttt.gtest
~~~~~~~~~~~~
This module implements the gtest execution wrapper. It will run a gtest binary
in a subprocess and capture its output to track the outcome of test execution.
:copyright: (c) yerejm
"""
import collections
import re
import termstyle
import os
import sys

from ttt.terminal import Terminal

TESTCASE_START_RE = re.compile('^\[----------\] \d+ tests? from (.*?)$')
TESTCASE_END_RE = re.compile(
    '^\[----------\] \d+ tests? from (.*?) \(\d+ ms total\)$'
)
TEST_START_RE = re.compile('^\[ RUN      \] (.*?)$')
TEST_END_RE = re.compile('^\[  (FAILED |     OK) \] (.*?)$')
TESTCASE_TIME_RE = re.compile(
    '^\[==========\] \d tests? from \d test cases? ran. \((\d+) ms total\)$'
)
# The patterns above are to match against the relevant output of a gtest run.
# TESTCASE refers to a group of TESTs. There can be more than one TESTCASE per
# gtest run.
#
# The output of a gtest binary on success:
#
# Running main() from gtest_main.cc
# [==========] Running 4 tests from 1 test case.
# [----------] Global test environment set-up.
# [----------] 4 tests from core
# [ RUN      ] core.ok
# [       OK ] core.ok (0 ms)
# [ RUN      ] core.okshadow
# [       OK ] core.okshadow (0 ms)
# [ RUN      ] core.notok
# [       OK ] core.notok (0 ms)
# [ RUN      ] core.blah
# [       OK ] core.blah (0 ms)
# [----------] 4 tests from core (1 ms total)
#
# [----------] Global test environment tear-down
# [==========] 4 tests from 1 test case ran. (1 ms total)
# [  PASSED  ] 4 tests.
#
# The output of a gtest binary on failure:
#
# Running main() from gtest_main.cc
# [==========] Running 4 tests from 1 test case.
# [----------] Global test environment set-up.
# [----------] 4 tests from core
# [ RUN      ] core.ok
# /path/to/project/test/test_core.cc:12: Failure
# Value of: 4
# Expected: ok()
# Which is: 42
# [  FAILED  ] core.ok (0 ms)
# [ RUN      ] core.okshadow
# [       OK ] core.okshadow (0 ms)
# [ RUN      ] core.notok
# [       OK ] core.notok (0 ms)
# [ RUN      ] core.blah
# [       OK ] core.blah (0 ms)
# [----------] 4 tests from core (0 ms total)
#
# [----------] Global test environment tear-down
# [==========] 4 tests from 1 test case ran. (0 ms total)
# [  PASSED  ] 3 tests.
# [  FAILED  ] 1 test, listed below:
# [  FAILED  ] core.ok
#
#  1 FAILED TEST
#


def testcase_starts_at(line):
    """Indicates if the line is the start of a testcase."""
    return TESTCASE_START_RE.match(line)


def testcase_ends_at(line):
    """Indicates if the line is the end of a testcase."""
    return TESTCASE_END_RE.match(line)


def test_starts_at(line):
    """Indicates if the line is the start of a test."""
    return TEST_START_RE.match(line)


def test_ends_at(line):
    """Indicates if the line is the end of a test."""
    return TEST_END_RE.match(line)


def test_elapsed_at(line):
    """Indicates if the line contains the time statistic for the testcase."""
    return TESTCASE_TIME_RE.match(line)


class GTest(object):
    """Representation of the execution, output capture and output parsing of a
    gtest-based binary.

    By default, the output of a :class:`GTest` object when executing its test
    is a summary, noting the test source file name, the test case, and a . or F
    to indicate the pass or fail state respectively for each test.
    e.g. sanity/test/test_core.cc :: core ....
    """
    WAITING_TESTCASE, WAITING_TEST, IN_TEST = range(3)

    def __init__(self, source, executable, term=None):
        """Creates a representation of a GTest binary.

        :param source: Path of the test source file
        :param executable: Path of the test executable
        :param term: (optional) Terminal object to send output of test
        execution. Default Terminal() will send no output.
        """
        if not source:
            raise Exception('Invalid source')
        if not executable:
            raise Exception('Invalid executable')

        self._source = source
        self._executable = executable
        self._term = term if term else Terminal()
        self._reset()

    def _reset(self):
        self._output = []
        self._error = []
        self._tests = collections.OrderedDict()
        self._state = GTest.WAITING_TESTCASE
        self._testcase = None
        self._test = None
        self._elapsed = 0
        self._pass_count = 0
        self._fail_count = 0

    def passes(self):
        """The number of passing tests detected in the latest test run."""
        return self._pass_count

    def fails(self):
        """The number of failing tests detected in the latest test run."""
        return self._fail_count

    def source(self):
        """The relative path to the test source file."""
        return self._source

    def executable(self):
        """The absolute path to the gtest binary executable."""
        return self._executable

    def run_time(self):
        """The elapsed time in milliseconds to run the tests."""
        return self._elapsed

    def execute(self, test_filters):
        """Executes the test executable, with this instance as a line listener.

        :param test_filters: a list of tests identified by name to be executed.
            This is a passed through as a colon separated string to the
            --gtest_filter command line option.
        :return a list of failing tests identified by name
        """
        from ttt.subproc import streamed_call
        command = [self.executable()]
        if test_filters:
            command.append("--gtest_filter={}".format(':'.join(test_filters)))
        self._reset()
        self._term.writeln("Executing {}".format(" ".join(command)), verbose=2)
        rc, stdout, stderr = streamed_call(command, listener=self)
        self._term.writeln(command, verbose=2)
        self._term.writeln(os.linesep.join(stdout), verbose=2)
        self._term.writeln(os.linesep.join(stderr), verbose=2)
        return self.failures()

    def failures(self):
        """Gets the list of tests that failed by name."""
        # results[0] is the first item in the results tuple. This is the
        # boolean indicator oof test failure.
        return [test for test, results in self._tests.items() if results[0]]

    def __call__(self, channel, line):
        """Listener interface for lines output during test execution.

        :class:`GTest` presents this callable interface intended for use by the
        :class:`SystemContext`.streamed_call as a line listener. Each line
        output during the execution of the tests is fed into __call__ (see
        execute()).
        """

        self.line(line)
        if channel == sys.stdout:
            self._output.append(line)
        else:
            self._error.append(line)

        # Track what the test execution is currently doing as a state.
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

    def line(self, line):
        """Line handler that will recolourise lines in the same manner as gtest
        when verbose mode is enabled.

        A gtest detects where it is being run and colorises output accordingly.
        This means that when run in a subprocess, it will not colorise output.
        """
        leader = line[:13]
        trailer = line[13:]

        decorator = [
            termstyle.bold,
            termstyle.red if '[  FAILED  ]' in line else termstyle.green
        ] if '[' in leader else []
        self._term.writeln(leader, decorator=decorator, end='', verbose=1)
        self._term.writeln(trailer, verbose=1)

    def begin_testcase(self, line):
        """Tracks when a test case starts.

        Output is suppressed in verbose mode because line() will have output
        the gtest actual output.
        """
        testcase = line[line.rfind(' ') + 1:]
        self._testcase = testcase

        self._term.writeln('{} :: {} '.format(str(self._source), testcase),
                           end='',
                           verbose=0)

    def end_testcase(self, line):
        """Tracks when a test case ends.

        Output is suppressed in verbose mode because line() will have output
        the gtest actual output.
        """
        self._testcase = None

        self._term.writeln(verbose=0)

    def begin_test(self, line):
        """Tracks when a test starts."""
        test = line[line.rfind(' ') + 1:]
        self._test = test
        self._output = []
        self._error = []

    def end_test(self, line):
        """Tracks when a test ends and whether it passed or failed.

        When not in verbose mode, a summary result is output (. for success, F
        for failure).

        Output is suppressed in verbose mode because line() will have output
        the gtest actual output.

        If the test failed, the output is captured.
        """
        if self._testcase is None:
            raise Exception('Invalid current testcase')
        if self._test is None:
            raise Exception('Invalid current test')
        failed = '[  FAILED  ]' in line
        self._tests[self._test] = (
            failed,
            self._output[:-1],  # cut the [ OK/FAILED ] line
            self._error[:],
        )
        self._current_test = None

        if failed:
            self._fail_count += 1
            self._term.writeln('F', end='', verbose=0)
        else:
            self._pass_count += 1
            self._term.writeln('.', end='', verbose=0)

    def results(self):
        """Gets the test results of the last test execution.

        This may not contain all possible tests due to the presence of a test
        filter (see execute()).

        This is a Dict() of test name key to a tuple of:
          - pass/fail indicator
          - whatever appeared on the stdout stream during test execution
          - whatever appeared on the stderr stream during test execution
        """
        return self._tests

    def test_results(self, testname):
        """Gets the test results for a particular test."""
        return self._tests[testname]
