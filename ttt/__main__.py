from __future__ import unicode_literals
import sys
import os
import time

import colorama

if sys.version_info < (3,):
    text_type = unicode
    binary_type = str
else:
    text_type = str
    binary_type = bytes


from ttt import cmake
from ttt import watcher
from ttt import executor
from ttt import systemcontext

RUNNING, STOPPING, FORCED_RUNNING = range(3)
DEFAULT_BUILD_PATH_SUFFIX = '-build'

def make_build_path(watch_path, suffix=DEFAULT_BUILD_PATH_SUFFIX):
    return os.path.join(
        os.getcwd(),
        "{}{}".format(os.path.basename(watch_path), suffix)
    )

def main():
    watch_path = os.path.abspath(sys.argv[1])
    build_path = make_build_path(watch_path)

    sc = systemcontext.SystemContext()
    ctx = cmake.CMakeContext(sc)

    w = watcher.Watcher(sc)
    t = executor.Executor(sc)

    runstate = FORCED_RUNNING

    delay = 1
    while runstate != STOPPING:
        try:
            time.sleep(delay)

            watchstate = w.poll(watch_path)
            if watchstate.has_changed() or runstate == FORCED_RUNNING:
                runstate = RUNNING
                ctx.build(watch_path, build_path)
                results = t.test(build_path, w.testdict())
                report_failures(results, watch_path)

        except KeyboardInterrupt:
            if runstate == FORCED_RUNNING:
                runstate = STOPPING
            else:
                runstate = FORCED_RUNNING
                print("\nInterrupt again to exit.")
        except cmake.CMakeError:
            pass

    print("\nWatching stopped.")

def report_failures(results, watch_path):
    runtime = 0
    fail_count = 0
    if results:
        stdout_write('=================================== FAILURES ===================================\n')
        for test in results:
            runtime += test.run_time()
            failures = test.failures()
            fail_count += len(failures)
            test_results = test.results()
            for testname, testresult in test_results.items():
                if testresult:
                    stdout_write('\n____________________________ {} ____________________________\n'.format(testname))
                    stdout_write('\n'.join(testresult[1:]))
                    stdout_write('\n\n')
                    stdout_write(testresult[0][len(watch_path) + 1:])
                    stdout_write('\n')
        stdout_write('=========================== {} failed in {} seconds ===========================\n'.format(fail_count, runtime/1000))

def stdout_write(string):
    sys.stdout.write(text_type(string))

if __name__ == "__main__":
    colorama.init()
    main()

