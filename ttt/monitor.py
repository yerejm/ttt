import os
import time
import collections
import itertools

from ttt.builder import create_builder
from ttt.watcher import watch, derive_tests, has_changes
from ttt.executor import create_executor
from ttt.reporter import create_reporter
from ttt.reporter import IRCReporter


DEFAULT_BUILD_PATH_SUFFIX = '-build'


def create_monitor(context, watch_path=os.getcwd(), **kwargs):
    watcher = watch(context, watch_path)
    custom_build_path = kwargs.get('build_path')
    build_path = (os.path.abspath(custom_build_path) if custom_build_path
                  else make_build_path(watcher.watch_path))
    builder = create_builder(
        context,
        watcher.watch_path,
        build_path,
        kwargs.get('generator')
    )
    executor = create_executor(context, build_path)
    terminal_reporter = create_reporter(context, watcher.watch_path, build_path)
    reporters = [terminal_reporter]
    if 'irc_server' in kwargs:
        reporters.append(IRCReporter(
            kwargs.get('irc_server'),
            kwargs.get('irc_port'),
            kwargs.get('irc_channel'),
            kwargs.get('irc_nick')
        ))

    return Monitor(watcher, builder, executor, reporters)


def make_build_path(watch_path, suffix=DEFAULT_BUILD_PATH_SUFFIX):
    return os.path.join(
        os.getcwd(),
        "{}{}".format(os.path.basename(watch_path), suffix)
    )


class Monitor(object):
    DEFAULT_POLLING_INTERVAL = 1

    def __init__(self, watcher, builder, executor, reporters, **kwargs):
        self.watcher = watcher
        self.builder = builder
        self.executor = executor
        self.reporters = reporters

        self.operations = Operations()
        self.runstate = Runstate()
        self.last_failed = 0
        self.polling_interval = first_value(kwargs.get('interval'),
                                            Monitor.DEFAULT_POLLING_INTERVAL)

        self.watcher.poll()

    def notify(self, message, *args):
        """
        Notifies all registered reporters for the given message. It is expected
        that the message given complies with what is expected by the Reporter
        interface.
        """
        for r in self.reporters:
            try:
                command = getattr(r, message)
                command(*args)
            except AttributeError:
                pass

    def report_change(self, watchstate):
        def fn():
            self.notify('report_watchstate', watchstate)
        return fn

    def build(self):
        def fn():
            self.notify('session_start', 'build')
            self.notify('report_build_path')
            try:
                self.builder()
            except IOError:
                self.operations.reset()
        return fn

    def test(self):
        def fn():
            self.notify('session_start', 'test')
            results = self.executor.test(
                derive_tests(self.watcher.filelist.values())
            )
            self.notify('report_results', results)

            if results['total_failed'] == 0 and self.last_failed > 0:
                self.last_failed = 0
                self.operations.append(self.test())
            self.last_failed = results['total_failed']
        return fn

    def run(self, **kwargs):
        step_mode = first_value(kwargs.get('step'), False)
        while self.runstate.active():
            self.check_for_changes()
            self.wait()

            if step_mode:
                break

    def check_for_changes(self):
        try:
            watchstate = self.watcher.poll()
            if has_changes(watchstate) or self.runstate.allowed_once():
                self.operations.append(
                    self.report_change(watchstate),
                    self.build(),
                    self.test()
                )
                self.operations.run()
                self.notify('wait_change')
        except KeyboardInterrupt as e:
            self.notify('report_interrupt', e)

    def wait(self):
        try:
            self.notify('wait')
            time.sleep(self.polling_interval)
        except KeyboardInterrupt:
            self.notify('interrupt_detected')
            self.executor.clear_filter()
            self.verify_stop()

    def verify_stop(self):
        try:
            time.sleep(self.polling_interval)
            self.runstate.allow_once()
        except KeyboardInterrupt:
            self.notify('halt')
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
