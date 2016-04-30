"""
ttt.executor
~~~~~~~~~~~~
This module implements the test executor. It assumes the tests being executed
are based on gtest.
:copyright: (c) yerejm
"""
import os
import stat

from ttt.gtest import GTest


class Executor(object):
    """Maintains the collection of tests detected by the :class:`Watcher` and
    provides an interface to execute all or some of those tests."""

    def __init__(self, context, build_path):
        self._context = context
        self._build_path = build_path
        self._test_filter = {}

    def test_filter(self):
        return self._test_filter

    def clear_filter(self):
        self._test_filter.clear()

    def test(self, testfiles):
        """Executes the tests named and identifiable as executable test binaries.

        This is a stateful method. When tests run, the :class:`Executor` will
        look for the presence of failing tests when running all the identified
        tests. If any are detected, the test filter will be applied and only
        those tests identified by the filter will run until all are passing
        again. At this point, the :class:`Executor` will be able to run all
        tests again and the cycle restarts.

        :param testfiles: a list of paths to possible test binaries
        :return a Dict() of test results containing:
          - total_runtime: time to run all tests in seconds
          - total_passed: the number of successful tests
          - total_failed: the number of failed tests (should equal the length
                of the failures list)
          - failures: a list of lists containing the failure results
        """
        testlist = [
            GTest(testfiles[f], os.path.join(d, f), self._context)
            for d, f, m, t in self._context.walk(self._build_path)
            if f in testfiles and m & stat.S_IXUSR
        ]
        test_results = run_tests(self._context, testlist, self._test_filter)
        self._test_filter = {
            test.executable(): test.failures()
            for test in test_results if test.failures()
        }
        return collate(test_results)


def collate(test_results):
    """Collate the test results of the failures into a Dict().

    See Executor.test().
    """
    runtime = 0.0
    fail_count = 0
    pass_count = 0
    failures = []
    for test in test_results:
        runtime += test.run_time()
        fail_count += test.fails()
        pass_count += test.passes()
        for failure in test.failures():
            failed, out, err = test.test_results(failure)
            failures.append([failure, out, err])
    runtime /= 1000  # runtime is in milliseconds; summarise using seconds

    return {
        'total_runtime': runtime,
        'total_passed': pass_count,
        'total_failed': fail_count,
        'failures': failures,
    }


def run_tests(context, testlist, test_filter):
    """Runs the available tests.

    If a test filter is provided, only those tests are run, and only failures
    for those tests are returned. This means than if a test in the filter is
    detected to fail, no other test is allowed to run until that test is
    passing while the ttt session remains running. This does not persist across
    ttt sessions.

    Otherwise, all tests are run, no matter how many tests are detected to have
    failed. This then feeds into the behaviour that requires failing tests to
    pass first before all tests can run again.

    :param context: the :class:`SystemContext` that will execute the test
        as a subprocess
    :param testlist: the list of available test executables
    :param test_filter: the list of test names to use as a filter to control
        which tests are run when executing the test executable
    :return a set of tests that ran
    """
    results = set()
    for test in testlist:
        context.writeln("Executing {}".format(test.executable()), verbose=2)
        if not test_filter or test.executable() in test_filter:
            failures = test.execute(
                context,
                test_filter[test.executable()] if test_filter else []
            )
            results.add(test)
            if failures and test_filter:
                break
    return results
