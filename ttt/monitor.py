import os
import time
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

class Reporter(object):

    def __init__(self, context):
        self.context = context

    def session_start(self):
        self.writeln('test session starts',
                decorator=[termstyle.bold], pad='=')

    def wait_change(self, watch_path):
        self.writeln('waiting for changes',
                decorator=[termstyle.bold], pad='#')
        self.writeln('### Watching:   {}'.format(watch_path),
                decorator=[termstyle.bold])

    def report_results(self, results, watch_path):
        runtime = 0
        fail_count = 0
        pass_count = 0
        for test in results:
            runtime += test.run_time()
            fail_count += test.fails()
            pass_count += test.passes()
        runtime /= 1000

        shortstats = '{} passed in {} seconds'.format(pass_count, runtime)
        if fail_count > 0:
            self.report_failures(results, watch_path)
            self.writeln('{} failed, {}'.format(fail_count, shortstats),
                    decorator=[termstyle.red,termstyle.bold], pad='=')
        else:
            self.writeln(shortstats,
                    decorator=[termstyle.green,termstyle.bold], pad='=')

    def report_failures(self, results, watch_path):
        self.writeln('FAILURES', pad='=')
        for test in results:
            test_results = test.results()
            for testname, testresult in test_results.items():
                if testresult:
                    self.writeln(testname,
                            decorator=[termstyle.red, termstyle.bold], pad='_')
                    self.writeln(os.linesep.join(testresult[1:]))
                    self.writeln()
                    self.writeln(testresult[0][len(watch_path) + 1:])

    def report_changes(self, watch_state):
        def print_changes(change, filelist):
            for f in filelist:
                self.writeln('# {} {}'.format(change, f))
        print_changes('CREATED', watch_state.inserts)
        print_changes('MODIFIED', watch_state.updates)
        print_changes('DELETED', watch_state.deletes)

    def interrupt_detected(self):
        self.writeln()
        self.writeln("Interrupt again to exit.")

    def halt(self):
        self.writeln()
        self.writeln("Watching stopped.")

    def writeln(self, *args, **kwargs):
        self.context.writeln(*args, **kwargs)

class Monitor(object):
    def __init__(self, watch_path, sc):
        self.watch_path = watch_path
        self.sc = sc
        self.build_path = make_build_path(watch_path)
        self.cmake = cmake.CMakeContext(sc)
        self.w = w = watcher.Watcher(sc)
        self.reporter = Reporter(sc)
        self.t = executor.Executor(sc)

    def activate(self, delay):
        watch_path = self.watch_path
        build_path = self.build_path
        r = self.reporter
        w = self.w
        w.poll(watch_path)
        t = self.t
        c = self.cmake

        runstate = FORCED_RUNNING
        while runstate != STOPPING:
            try:
                time.sleep(delay)

                watchstate = w.poll(watch_path)
                if watchstate.has_changed() or runstate == FORCED_RUNNING:
                    runstate = RUNNING

                    r.report_changes(watchstate)
                    c.build(watch_path, build_path)
                    r.session_start()
                    results = t.test(build_path, w.testdict())
                    r.report_results(results, watch_path)
                    r.wait_change(watch_path)

            except KeyboardInterrupt:
                t.clear_filter()
                if runstate == FORCED_RUNNING:
                    runstate = STOPPING
                else:
                    runstate = FORCED_RUNNING
                    r.interrupt_detected()
            except cmake.CMakeError:
                pass

        r.halt()

