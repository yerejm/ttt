import os
import time
import collections
import itertools

from ttt.builder import create_builder
from ttt.watcher import create_watcher
from ttt.executor import create_executor
from ttt.reporter import create_reporter

DEFAULT_BUILD_PATH_SUFFIX = '-build'

def create_monitor(context, watch_path=os.getcwd(), **kwargs):
    watcher = create_watcher(context, watch_path)
    custom_build_path = kwargs.get('build_path')
    build_path = os.path.abspath(custom_build_path) if custom_build_path else make_build_path(watcher.watch_path)
    builder = create_builder(context, watcher.watch_path, build_path, kwargs.get('generator'))
    executor = create_executor(context, build_path)
    reporter = create_reporter(context, watcher.watch_path, build_path)
    return Monitor(context, watcher, builder, executor, reporter)

def make_build_path(watch_path, suffix=DEFAULT_BUILD_PATH_SUFFIX):
    return os.path.join(
        os.getcwd(),
        "{}{}".format(os.path.basename(watch_path), suffix)
    )

class Monitor(object):
    DEFAULT_POLLING_INTERVAL = 1

    def __init__(self, context, watcher, builder, executor, reporter, **kwargs):
        self.watcher = watcher
        self.builder = builder
        self.executor = executor
        self.reporter = reporter

        self.operations = Operations()
        self.runstate = Runstate()
        self.last_failed = 0
        self.polling_interval = first_value(kwargs.get('interval'), Monitor.DEFAULT_POLLING_INTERVAL)

        self.watcher.poll()

    def report_change(self, watchstate):
        def fn():
            self.reporter.report_watchstate(watchstate)
        return fn

    def build(self):
        def fn():
            self.reporter.session_start('build')
            self.reporter.report_build_path('build')
            try:
                self.builder.build()
            except builder.CMakeError:
                self.operations.reset()
        return fn

    def test(self):
        def fn():
            self.reporter.session_start('test')
            results = self.executor.test(self.watcher.testdict())
            self.reporter.report_results(results)

            if results['total_failed'] == 0 and self.last_failed > 0:
                self.last_failed = 0
                self.operations.append(self.test())
            self.last_failed = results['total_failed']
        return fn

    def run(self):
        while self.runstate.active():
            try:
                watchstate = self.watcher.poll()
                if watchstate.has_changed() or self.runstate.allowed_once():
                    self.operations.append(
                        self.report_change(watchstate),
                        self.build(),
                        self.test()
                    )
                    self.operations.run()
                    self.reporter.wait_change()
            except KeyboardInterrupt as e:
                self.reporter.report_interrupt(e)
            try:
                time.sleep(self.polling_interval)
            except KeyboardInterrupt:
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
        self._allow_once = True

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

class Operations(object):
    def __init__(self):
        self.execution_stack = collections.deque()

    def append(self, *args):
        for op in args:
            self.execution_stack.append(op)

    def operations(self):
        return [ fn for fn in self.execution_stack ]

    def run(self):
        try:
            while True:
                self.execution_stack.popleft()()
        except IndexError:
            pass
        except KeyboardInterrupt:
            self.reset()
            raise

    def reset(self):
        self.execution_stack.clear()

def first_value(*args):
    return next(itertools.dropwhile(lambda x: x is None, args), None)

