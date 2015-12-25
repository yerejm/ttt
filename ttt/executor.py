import os
import subprocess
import stat

from ttt import subproc
from ttt.gtest import GTest
from ttt.systemcontext import SystemContext

class Executor(object):
    def __init__(self, build_path):
        self.test_filter = {}
        self.provider = FileProvider(SystemContext(build_path))

    def test(self, testfiles):
        test_filter = self.test_filter
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

def create_tests(provider, testfiles):
    tests = []
    for buildfile in provider.glob_files(lambda x: x in testfiles):
        if buildfile.is_executable_file():
            filepath = buildfile.path()
            tests.append(GTest(testfiles[os.path.basename(filepath)], filepath))
    return tests

class BuildFile(object):
    """ Represents a file located within the build area. """

    def __init__(self, path, name, statmode):
        self._name = name
        self._path = path
        self._statmode = statmode

    def name(self):
        """ The name of the file (basename) """
        return self._name

    def path(self):
        """ The absolute path to the file """
        return os.path.join(self._path, self._name)

    def is_executable_file(self):
        """ Indicates the file is executable """
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

class FileProvider(object):
    def __init__(self, file_system):
        self.file_system = file_system

    def glob_files(self, selector):
        for dirpath, filename, statmode in self.file_system.walk():
            if selector(filename):
                yield BuildFile(dirpath, filename, statmode)

    def execute(self, cmd):
        return self.file_system.execute(cmd).splitlines()

    def streamed_call(self, command, listener):
        return subproc.call_output(command, universal_newlines=True, line_handler=listener)

