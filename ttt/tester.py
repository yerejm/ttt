import os
import collections
import subprocess
import re
import termstyle
import colorama
import platform
import stat

from ttt import subproc

TestFile = collections.namedtuple(
    "TestFile",
    [ "prefix", "testname", "filename" ]
)
TestFile.__new__.__defaults__ = (None, None, None)
Test = collections.namedtuple(
    "Test",
    [ "testgroup", "testcases", "abspath" ]
)
Test.__new__.__defaults__ = (None, None, None)

class Tester(object):
    def __init__(self, build_path):
        colorama.init()
        self.test_filter = []
        self.build_path = build_path

    def test(self, filelist):
        test_filter = self.test_filter
        testpatterns = derive_test_patterns(filelist, 'test_')
        testlist = get_test_files(self.build_path, testpatterns)
        try:
            if test_filter:
                for test in testlist:
                    results = run_test(test, test_filter)
                    test_filter = failing_tests(results, testpatterns)
                    if test_filter:
                        raise
            test_filter = []
            for test in testlist:
                results = run_test(test, test_filter)
                test_filter = failing_tests(results, testpatterns)
        except:
            pass
        self.test_filter = test_filter

def is_executable_test(dirpath, filename, patterns):
    abspath = os.path.join(dirpath, filename)
    for pattern in patterns:
        if filename == pattern.filename and (os.stat(abspath).st_mode & stat.S_IXUSR):
            return True
    return False

def create_test(path):
    try:
        output = subprocess.check_output(
            [path, '--gtest_list_tests'],
            universal_newlines=True
        )
        lines = output.splitlines()
        testgroup = lines[1][0:-1]
        testcases = [ case.strip() for case in lines[2:] ]
        print("{} -> {}".format(testgroup, testcases))
        return Test(abspath=path, testgroup=testgroup, testcases=testcases)
    except subprocess.CalledProcessError as e:
        print("Skipping {}: {}".format(path, e))
    return None

def get_test_files(root_directory, patterns):
    files = []
    for dirpath, dirlist, filelist in os.walk(root_directory):
        for filename in filelist:
            if is_executable_test(dirpath, filename, patterns):
                abspath = os.path.join(dirpath, filename)
                test = create_test(abspath)
                if test:
                    files.append(test)
    return files

def exe_suffix():
    return ".exe" if platform.system() == 'Windows' else ""

def derive_test_patterns(source_files, test_prefix):
    test_patterns = set()
    pattern = re.compile("^{}(.*?)\.".format(test_prefix))
    for filename in source_files.keys():
        matches = pattern.match(source_files[filename].filename)
        if matches:
            test_patterns.add(
                TestFile(
                    prefix=test_prefix,
                    testname=matches.group(1),
                    filename="{}{}{}".format(
                        test_prefix,
                        matches.group(1),
                        exe_suffix())
                )
            )
    return test_patterns

def run_test(test, test_filter):
    test_results = []
    def fails(line):
        test_results.append(line)
        colorer = termstyle.red if 'FAILED' in line else termstyle.green
        brightness = colorama.Style.BRIGHT if platform.system() == 'Windows' else colorama.Style.NORMAL
        if line[:1] == '[':
            return '{}{}{}{}'.format(brightness, colorer(line[:13]), termstyle.reset, line[13:])

    command = [test.abspath]
    # command.append('--gtest_color=yes')
    if test_filter:
        command.append("--gtest_filter={}".format(':'.join(test_filter)))
    print("Run {}".format(command))
    subproc.call_output(command, universal_newlines=True, line_handler=fails)
    return test_results 

def failing_tests(failures, patterns):
    failed = []
    for line in reversed(failures):
        if "==========" in line:
            break;
        for pattern in patterns:
            # print("search: {} in {}".format(pattern.testname, line))
            if pattern.testname in line and "FAILED" in line:
                matcher = re.compile("{}\..*?$".format(pattern.testname))
                matches = matcher.search(line)
                failed.append(matches.group(0).strip())
    return failed

