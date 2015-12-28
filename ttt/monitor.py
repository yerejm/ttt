import os
import time
import termstyle

from ttt import cmake
from ttt import watcher
from ttt import executor

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

    def report_results(self, results):
        shortstats = '{} passed in {} seconds'.format(
                results['total_passed'],
                results['total_runtime']
                )
        total_failed = results['total_failed']
        if total_failed > 0:
            self.report_failures(results['failures'])
            self.writeln('{} failed, {}'.format(total_failed, shortstats),
                    decorator=[termstyle.red,termstyle.bold], pad='=')
        else:
            self.writeln(shortstats,
                    decorator=[termstyle.green,termstyle.bold], pad='=')

    def report_failures(self, results):
        self.writeln('FAILURES', pad='=')
        for testname, testresult in results:
            self.writeln(testname,
                    decorator=[termstyle.red, termstyle.bold], pad='_')
            self.writeln(os.linesep.join(testresult[1:]))
            self.writeln()
            self.writeln(testresult[0])

    def report_changes(self, change, filelist):
        for f in filelist:
            self.writeln('# {} {}'.format(change, f))

    def interrupt_detected(self):
        self.writeln()
        self.writeln("Interrupt again to exit.")

    def halt(self):
        self.writeln()
        self.writeln("Watching stopped.")

    def writeln(self, *args, **kwargs):
        self.context.writeln(*args, **kwargs)

class Monitor(object):
    DEFAULT_POLLING_INTERVAL = 1

    def __init__(self, watch_path, sc, **kwargs):
        self.watch_path = watch_path
        self.build_path = make_build_path(watch_path)
        self.cmake = cmake.CMakeContext(sc)
        self.watcher = watcher.Watcher(sc)
        self.reporter = Reporter(sc)
        self.executor = executor.Executor(sc)

        if 'interval' in kwargs:
            self.polling_interval = kwargs['interval']
        else:
            self.polling_interval = Monitor.DEFAULT_POLLING_INTERVAL

        self.runstate = Runstate()
        self.watchcycle()

    def run(self):
        while self.runstate.active():
            self.activate()

    def activate(self):
        try:
            self.watchcycle(report_watchstate=True)
            time.sleep(self.polling_interval)
        except KeyboardInterrupt:
            self.handle_keyboard_interrupt()

    def watchcycle(self, **kwargs):
        watchstate = self.watcher.poll(self.watch_path)
        if watchstate.has_changed() or self.runstate.allowed_once():
            if 'report_watchstate' in kwargs and kwargs['report_watchstate']:
                self.print_watchstate(watchstate)
            self.process_change(self.watcher.testdict())
            self.reporter.wait_change(self.watch_path)

    def process_change(self, testdict):
        try:
            self.cmake.build(self.watch_path, self.build_path)
        except cmake.CMakeError:
            return

        self.reporter.session_start()
        results = self.executor.test(self.build_path, testdict)
        self.reporter.report_results(results)

    def print_watchstate(self, watchstate):
        r = self.reporter
        r.report_changes('CREATED', watchstate.inserts)
        r.report_changes('MODIFIED', watchstate.updates)
        r.report_changes('DELETED', watchstate.deletes)

    def handle_keyboard_interrupt(self):
        self.executor.clear_filter()
        self.verify_stop()

    def verify_stop(self):
        self.reporter.interrupt_detected()
        try:
            time.sleep(Monitor.DEFAULT_POLLING_INTERVAL)
            self.runstate.allow_once()
        except KeyboardInterrupt:
            self.reporter.halt()
            self.runstate.stop()

class Runstate(object):
    def __init__(self):
        self._active = True
        self._allow_once = False

    def active(self):
        return self._active

    def stop(self):
        self._active = False

    def allow_once(self):
        self._allow_once = True

    def allowed_once(self):
        allow_once = self._allow_once
        self._allow_once = False
        return allow_once

