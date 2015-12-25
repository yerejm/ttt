import os
import stat

from ttt.gtest import GTest

class Executor(object):
    def __init__(self, context):
        self.test_filter = {}
        self.context = context

    def test(self, build_path, testfiles):
        test_filter = self.test_filter
        testlist = create_tests(self.context, build_path, testfiles)

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
                test.execute(self.context, test_filter[test.executable()] if test_filter else [])
                failures = test.failures()
                if failures:
                    return { test.executable(): failures }
        return {}

def create_tests(context, build_path, testfiles):
    tests = []
    for dir, file, mode in context.glob_files(build_path, lambda x: x in testfiles):
        if mode & stat.S_IXUSR:
            filepath = os.path.join(dir, file)
            tests.append(GTest(testfiles[file], filepath))
    return tests

