import collections
import re

class GTest(object):
    WAITING_TESTCASE, WAITING_TEST, IN_TEST = range(3)
    TESTCASE_START_RE = re.compile('^\[----------\] \d+ tests? from (.*?)$')
    TESTCASE_END_RE   = re.compile('^\[----------\] \d+ tests? from (.*?) \(\d+ ms total\)$')
    TEST_START_RE     = re.compile('^\[ RUN      \] (.*?)$')
    TEST_END_RE       = re.compile('^\[  (FAILED |     OK) \] (.*?)$')
    TESTCASE_TIME_RE  = re.compile('^\[==========\] \d tests? from \d test cases? ran. \((\d+) ms total\)$')

    def __init__(self, source=None, executable=None, term=None):
        self._source = source
        self._executable = executable
        self._reset()
        self._term = term

    def _reset(self):
        self._output = []
        self._tests = collections.OrderedDict()
        self._state = GTest.WAITING_TESTCASE
        self._testcase = None
        self._test = None
        self._elapsed = 0
        self._pass_count = 0
        self._fail_count = 0

    def passes(self):
        return self._pass_count

    def fails(self):
        return self._fail_count

    def executable(self):
        return self._executable

    def run_time(self):
        return self._elapsed

    def execute(self, context, test_filters, **kwargs):
        verbose = 'verbose' in kwargs and kwargs['verbose']
        command = [ self.executable() ]
        if test_filters:
            command.append("--gtest_filter={}".format(':'.join(test_filters)))
        self._reset()
        rc, output = context.streamed_call(command, listener=self)
        if verbose:
            import os
            print(command)
            print(''.join(output))
        return self.failures()

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
            pos = line.find(self._source)
            if pos > 0:
                line = line[pos:]
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

        term = self._term
        if term is not None:
            term.write('{} :: {} '.format(str(self._source), testcase))

    def end_testcase(self, line):
        self._testcase = None

        term = self._term
        if term is not None:
            term.writeln()

    def begin_test(self, line):
        test = line[line.rfind(' ') + 1:]
        self._test = test
        self._output = []

    def end_test(self, line):
        if self._testcase is None:
            raise Exception('Invalid current testcase')
        if self._test is None:
            raise Exception('Invalid current test')
        self._tests[self._test] = self._output[:-1]
        self._current_test = None

        term = self._term
        if '[  FAILED  ]' in line:
            self._fail_count += 1
            if term is not None:
                term.write('F')
        else:
            self._pass_count += 1
            if term is not None:
                term.write('.')

    def results(self):
        return self._tests

    def test_results(self, testname):
        return self._tests[testname]

    def failures(self):
        failures = []
        for test, results in self._tests.items():
            if results:
                failures.append(test)
        return failures

