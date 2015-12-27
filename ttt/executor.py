import sys
import os
import stat

from ttt.gtest import GTest

class Executor(object):
    def __init__(self, context):
        self._test_filter = {}
        self.context = context

    def test_filter(self):
        return self._test_filter

    def clear_filter(self):
        self._test_filter.clear()

    def test(self, build_path, testfiles):
        test_filter = self.test_filter()
        testlist = create_tests(self.context, build_path, testfiles)
        test_results = set()

        if test_filter:
            test_results = run_tests(self.context, testlist, test_filter)
            test_filter = create_filter(test_results)

        if not test_filter:
            test_results = run_tests(self.context, testlist, set())
            test_filter = create_filter(test_results)

        self._test_filter = test_filter
        return test_results

def create_filter(test_results):
    return { test.executable(): test.failures() for test in test_results if test.failures() }

def run_tests(context, testlist, test_filter):
    results = set()
    for test in testlist:
        if not test_filter or test.executable() in test_filter:
            failures = test.execute(context, test_filter[test.executable()] if test_filter else [])
            results.add(test)
            if failures and test_filter:
                break
    return results

def create_tests(context, build_path, testfiles):
    def is_executable_test(x):
        d, f, m = x
        return f in testfiles and m & stat.S_IXUSR

    tests = []
    for dir, file, mode in filter(is_executable_test, context.walk(build_path)):
        filepath = os.path.join(dir, file)
        tests.append(GTest(testfiles[file], filepath))
    return tests

