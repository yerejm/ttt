import sys
import subprocess
import os
import stat
import re
import glob
import multiprocessing
import time
import collections
import platform
import string

WatchedFile = collections.namedtuple(
    "WatchedFile",
    [ "filename", "mtime" ]
)
WatchedFile.__new__.__defaults__ = (None, None)
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
BUILD_SYSTEMS = {
    'Makefile': 'make -j{} -f',
    'build.ninja': 'ninja -j{} -f',
    '*.sln': 'msbuild /m:{}'
}

RUNNING = 1
STOPPING = 2
FORCED_RUNNING = 3

def cmake_initialise(source_directory, build_directory):
    command = "cmake {}".format(source_directory)
    print(command)
    subprocess.call(command, shell=True)

def derive_build_command(buildcommand, buildfile):
    parallelism = multiprocessing.cpu_count() + 2
    print("Determining build command for {}".format(buildfile))
    return "{} {}".format(buildcommand.format(parallelism), buildfile)

def find_build_file(search_path):
    print("Searching for build file {}".format(search_path))
    matches = glob.glob(search_path)
    if not matches:
        return None
    if len(matches) > 1:
        print("WARNING: Multiple build files detected!")
    return os.path.basename(matches[0])

def discover_build_command(directory):
    for (buildfile_pattern, buildcommand) in BUILD_SYSTEMS.items():
        buildfile = find_build_file(os.path.join(directory, buildfile_pattern))
        if buildfile and os.path.exists(buildfile):
            return derive_build_command(buildcommand, buildfile)
    return None

def is_watchable(filename, patterns):
    for pattern in patterns:
        if pattern.search(filename):
            return True
    return False

def get_watched_files(root_directory, patterns):
    files = dict()
    for dirpath, dirlist, filelist in os.walk(root_directory):
        for filename in filelist:
            if is_watchable(filename, patterns):
                watched_file = os.path.join(dirpath, filename)
                files[watched_file] = WatchedFile(
                    filename=filename,
                    mtime=os.path.getmtime(watched_file)
                )
    return files

def is_executable_test(dirpath, filename, patterns):
    abspath = os.path.join(dirpath, filename)
    for pattern in patterns:
        if filename == pattern.filename and (os.stat(abspath).st_mode & stat.S_IXUSR):
            return True
    return False

def create_test(path):
    try:
        output = subprocess.check_output(
            "{} --gtest_list_tests".format(path),
            shell=True,
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

class WatchState(object):
    def __init__(self, inserts, deletes, updates):
        self.inserts = inserts
        self.deletes = deletes
        self.updates = updates

    def has_changed(self):
        return self.inserts or self.deletes or self.updates

    def print_changes(self):
        for filename in self.inserts:
            print("INSERT: {}".format(filename))
        for filename in self.deletes:
            print("DELETE: {}".format(filename))
        for filename in self.updates:
            print("UPDATE: {}".format(filename))

def create_watchstate(dictA, dictB):
    dictAKeys = set(dictA.keys())
    dictBKeys = set(dictB.keys())
    inserts = dictBKeys - dictAKeys
    deletes = dictAKeys - dictBKeys
    updates = set()
    for filename in dictA.keys():
        if filename in dictB and dictB[filename].mtime != dictA[filename].mtime:
            updates.add(filename)
    return WatchState(inserts, deletes, updates)

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
    command = test.abspath
    if test_filter:
        command += " --gtest_filter={}".format(string.join(test_filter, ":"))
    print("Run {}".format(command))
    print(subprocess.check_output(command, shell=True))

def failing_tests(output, patterns):
    print(output)
    failed = []
    for line in reversed(output.splitlines()):
        if "==========" in line:
            break;
        for pattern in patterns:
            # print("search: {} in {}".format(pattern.testname, line))
            if pattern.testname in line and "FAILED" in line:
                matcher = re.compile("{}\..*?$".format(pattern.testname))
                matches = matcher.search(line)
                failed.append(matches.group(0).strip())
    return failed

def main():
    watch_area = sys.argv[1]
    watch_path = os.path.abspath(watch_area)
    build_path = os.path.join(
        os.getcwd(),
        "{}-build".format(os.path.basename(watch_path))
    )
    print("Watching {}...".format(watch_path))
    if not os.path.exists(build_path):
        print("Creating build area {}".format(build_path))
        os.makedirs(build_path)
    os.chdir(build_path)
    if not os.path.exists(os.path.join(build_path, 'CMakeFiles')):
        cmake_initialise(watch_path, build_path)
    command = discover_build_command(build_path)
    if command is None:
        print("Unsupported build system.")
        sys.exit()

    source_patterns = [
        re.compile('\.cc$'),
        re.compile('\.c$'),
        re.compile('\.h$'),
        re.compile('CMakeLists.txt$'),
    ]

    filelist = get_watched_files(watch_path, source_patterns)
    testpatterns = derive_test_patterns(filelist, 'test_')

    runstate = FORCED_RUNNING
    delay = 1
    test_filter = []
    while runstate != STOPPING:
        try:
            time.sleep(delay)

            current_filelist = get_watched_files(watch_path, source_patterns)
            watchstate = create_watchstate(filelist, current_filelist)

            watchstate.print_changes()

            if watchstate.has_changed() or runstate == FORCED_RUNNING:
                runstate = RUNNING
                print(command)
                subprocess.call(command, shell=True) # build

                # test
                try:
                    testlist = get_test_files(build_path, testpatterns)
                    if test_filter:
                        for test in testlist:
                            run_test(test, test_filter)
                    test_filter = []
                    for test in testlist:
                        run_test(test, test_filter)
                except subprocess.CalledProcessError as e:
                    test_filter = failing_tests(e.output, testpatterns)

            filelist = current_filelist
        except KeyboardInterrupt:
            test_filter = []
            if runstate == FORCED_RUNNING:
                runstate = STOPPING
            else:
                runstate = FORCED_RUNNING
                print("\nInterrupt again to exit.")
    print("\nWatching stopped.")

if __name__ == "__main__":
    main()

