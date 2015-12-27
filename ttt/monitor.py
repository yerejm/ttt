import os
import sys
import time
from six import text_type
import termstyle

from ttt import cmake
from ttt import watcher
from ttt import executor

RUNNING, STOPPING, FORCED_RUNNING = range(3)
DEFAULT_BUILD_PATH_SUFFIX = '-build'

def make_build_path(watch_path, suffix=DEFAULT_BUILD_PATH_SUFFIX):
    return os.path.join(
        os.getcwd(),
        "{}{}".format(os.path.basename(watch_path), suffix)
    )

class Monitor(object):
    def __init__(self, watch_path, sc):
        self.watch_path = watch_path
        self.sc = sc
        self.build_path = make_build_path(watch_path)
        self.cmake = cmake.CMakeContext(sc)
        self.w = w = watcher.Watcher(sc)
        self.t = executor.Executor(sc)

    def activate(self, delay):
        watch_path = self.watch_path
        build_path = self.build_path
        w = self.w
        w.poll(watch_path)
        t = self.t
        cmake = self.cmake

        runstate = FORCED_RUNNING
        while runstate != STOPPING:
            try:
                time.sleep(delay)

                watchstate = w.poll(watch_path)
                if watchstate.has_changed() or runstate == FORCED_RUNNING:
                    report_changes(watchstate)

                    runstate = RUNNING
                    cmake.build(watch_path, build_path)
                    stdout_write(termstyle.bold(
                        '============================= test session starts ==============================\n'
                    ))
                    results = t.test(build_path, w.testdict())
                    report_failures(results, watch_path)
                    stdout_write(termstyle.bold(
                        '############################## waiting for changes ##############################\n'
                    ))
                    stdout_write(termstyle.bold(
                        '### Watching:   {}\n'.format(watch_path)
                    ))

            except KeyboardInterrupt:
                t.clear_filter()
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
    pass_count = 0
    for test in results:
        runtime += test.run_time()
        fail_count += test.fails()
        pass_count += test.passes()

    if fail_count > 0:
        stdout_write('=================================== FAILURES ===================================\n')
        for test in results:
            test_results = test.results()
            for testname, testresult in test_results.items():
                if testresult:
                    stdout_write(termstyle.red(termstyle.bold(
                        '\n____________________________ {} ____________________________\n'.format(testname)
                    )))
                    stdout_write('\n'.join(testresult[1:]))
                    stdout_write('\n\n')
                    stdout_write(testresult[0][len(watch_path) + 1:])
                    stdout_write('\n')
        stdout_write(termstyle.red(termstyle.bold(
            '=========================== {} failed in {} seconds ===========================\n'.format(fail_count, runtime/1000)
        )))
    else:
        stdout_write(termstyle.green(termstyle.bold(
            '========================== {} passed in {} seconds ===========================\n'.format(pass_count, runtime/1000)
        )))

def report_changes(watch_state):
    for f in watch_state.inserts:
        stdout_write('# CREATED {}\n'.format(f))
    for f in watch_state.updates:
        stdout_write('# MODIFIED {}\n'.format(f))
    for f in watch_state.deletes:
        stdout_write('# DELETED {}\n'.format(f))

def stdout_write(string):
    sys.stdout.write(text_type(string))

