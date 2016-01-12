import os
import stat

from ttt.gtest import GTest


def create_executor(context, build_path):
    return Executor(context, build_path)


class Executor(object):
    def __init__(self, context, build_path):
        self._context = context
        self._build_path = build_path
        self._test_filter = {}

    def test_filter(self):
        return self._test_filter

    def clear_filter(self):
        self._test_filter.clear()

    def test(self, testfiles):
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
    runtime /= 1000

    return {
        'total_runtime': runtime,
        'total_passed': pass_count,
        'total_failed': fail_count,
        'failures': failures,
    }


def run_tests(context, testlist, test_filter):
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
