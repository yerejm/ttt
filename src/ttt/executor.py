"""
ttt.executor
~~~~~~~~~~~~
This module implements the test executor. It assumes the tests being executed
are based on gtest.
:copyright: (c) yerejm
"""

PASSED = 0
FAILED = 1
CRASHED = 2


class Executor(object):
    """Maintains the collection of tests detected by the :class:`Watcher` and
    provides an interface to execute all or some of those tests."""

    def __init__(self):
        self._test_filter = {}

    def test_filter(self):
        return self._test_filter

    def clear_filter(self):
        self._test_filter.clear()

    def test(self, testlist):
        """Executes the tests provided in the given list.

        All tests are run and their outcome captured. If any failing tests are
        detected, a test filter is updated to record those failures. Once this
        occurs, only those tests identified by the filter will run until all
        have passed. At this point, the filter is empty.

        This means than if a test in the filter is detected to fail, no other
        test is allowed to run until that test is passing while the ttt session
        remains running. This does not persist across ttt sessions and the
        filter can be removed during a session using clear_filter().

        :param testlist: a list of test objects
        :return a Dict() of test results containing:
          - total_runtime: time to run all tests in seconds
          - total_passed: the number of successful tests
          - total_failed: the number of failed tests (should equal the length
                of the failures list)
          - failures: a list of lists containing the failure results
        """
        test_filter = self._test_filter
        test_results = set()
        for test in testlist:
            if not test_filter or test.executable() in test_filter:
                failures = test.execute(
                    test_filter[test.executable()] if test_filter else []
                )
                test_results.add(test)
                if failures and test_filter:
                    break

        # update the test filter for those tests that failed
        self._test_filter = {
            test.executable(): test.failures()
            for test in test_results
            if test.failures()
        }

        # collate the test results
        runtime = 0.0
        fail_count = 0
        pass_count = 0
        failures = []
        for test in test_results:
            runtime += test.run_time()
            fail_count += test.fails()
            pass_count += test.passes()
            for failed_test in test.failures():
                outcome, out, err = test.test_results(failed_test)
                failures.append([failed_test, out, err, outcome])
        runtime /= 1000  # runtime is in milliseconds; summarise using seconds

        return {
            "total_runtime": runtime,
            "total_passed": pass_count,
            "total_failed": fail_count,
            "failures": failures,
        }
