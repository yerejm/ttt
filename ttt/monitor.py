"""
ttt.monitor
~~~~~~~~~~~~
This module implements the monitor which will poll the watched source tree for
change and initiate the build and test of the watched source tree.
:copyright: (c) yerejm
"""
import collections
import itertools
import os
import socket
import subprocess
import sys
import time

from ttt.builder import create_builder
from ttt.watcher import Watcher, has_changes
from ttt.executor import Executor
from ttt.reporter import create_terminal_reporter, create_irc_reporter
from ttt.terminal import Terminal


DEFAULT_BUILD_PATH_SUFFIX = '-build'
DEFAULT_SOURCE_PATTERNS = [
    '\.cc$',
    '\.c$',
    '\.h$',
    'CMakeLists.txt$',
]


def create_monitor(context, watch_path=None, **kwargs):
    """Creates a monitor and its subordinate objects.

    By default, one reporter object is created to output to the terminal.
    An optional IRC reporter may be created if irc_server is provided.

    :param context:
    :param watch_path: the root of the source tree, either relative or
        absolute. If not provided, the current working directory is assumed to
        be the root of the source tree.
    :param build_path: (optional) the desired build path. May be relative. If
        not provided, it will be generated from the watch path.
    :param generator: (optional) the cmake build system generator
    :param irc_server: (optional) the IRC server host if an IRC reporter is
        required.
    :param irc_port (optional) the IRC server port. Has no meaning without
        irc_server.
    :param irc_channel (optional) the IRC channel to join once connected. Has
        no meaning without irc_server.
    :param irc_nick (optional) the IRC nickname to use once connected. Has
        no meaning without irc_server.
    """
    full_watch_path = os.path.abspath(
        os.getcwd() if watch_path is None else watch_path
    )
    if not os.path.exists(full_watch_path):
        import errno
        raise IOError(
            errno.ENOENT,
            "Invalid path: {} ({})".format(watch_path, full_watch_path)
        )
    custom_build_path = kwargs.get('build_path')
    build_path = (os.path.abspath(custom_build_path) if custom_build_path
                  else make_build_path(full_watch_path, kwargs.get('config')))
    watcher = Watcher(full_watch_path, build_path, DEFAULT_SOURCE_PATTERNS)
    builder = create_builder(
        context,
        watcher.watch_path,
        build_path,
        kwargs.get('generator'),
        kwargs.get('config')
    )
    terminal = Terminal(sys.stdout)
    executor = Executor(context, terminal)
    terminal_reporter = create_terminal_reporter(
        terminal,
        watcher.watch_path,
        build_path
    )
    reporters = [terminal_reporter]
    if 'irc_server' in kwargs and kwargs['irc_server'] is not None:
        reporters.append(
            create_irc_reporter(
                kwargs.get('irc_server'),
                kwargs.get('irc_port'),
                kwargs.get('irc_channel'),
                first_value(
                    kwargs.get('irc_nick'),
                    '{}-{}{}'.format(
                        socket.gethostname().split('.')[0],
                        os.path.basename(watch_path),
                        '-' + first_value(kwargs.get('config'), '')
                    )
                )
            )
        )

    return Monitor(watcher, builder, executor, reporters)


def make_build_path(watch_path,
                    build_type=None,
                    suffix=DEFAULT_BUILD_PATH_SUFFIX):
    """Creates a build path from the watch path by appending a suffix.

    The build path will be an absolute path based on the current working
    directory.

    :param watch_path: the watch path
    :param config: the build type
    :param suffix: (optional) the suffix to append to the watch path. Defaults
    to -build.
    :return the absolute build path
    """
    return os.path.join(
        os.getcwd(),
        "{}{}{}".format(os.path.basename(watch_path),
                        '' if build_type is None else ('-' + build_type),
                        suffix)
    )


class Monitor(object):
    """The main point of integration for the disparate parts.

    Observers of the monitor are notified for each state that provides a hook.
    """
    DEFAULT_POLLING_INTERVAL = 1

    def __init__(self, watcher, builder, executor, reporters, **kwargs):
        """:class:`Monitor` constructor.

        :param watcher: the :class:`Watcher` object
        :param builder: the :class:`Builder` object
        :param executor: the :class:`Executor` object
        :param reporters: a list of :class:`Reporter` objects (Monitor
        listeners)
        :param interval: (optional) the time in seconds to wait between
            checking for changes
        """
        self.watcher = watcher
        self.builder = builder
        self.executor = executor
        self.reporters = reporters

        self.operations = Operations()
        self.runstate = Runstate()
        self.last_failed = 0
        self.polling_interval = first_value(kwargs.get('interval'),
                                            Monitor.DEFAULT_POLLING_INTERVAL)

        # The first poll is to initialise the watcher with the source tree
        # before the actual polling loop.
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
        """Get a function that will notify observers that there was a change.
        """
        def fn():
            self.notify('report_watchstate', watchstate)
        return fn

    def build(self):
        """Builds the binaries."""
        def fn():
            self.notify('session_start', 'build')
            self.notify('report_build_path')
            try:
                self.builder()
            except KeyboardInterrupt as e:
                raise e
            except subprocess.CalledProcessError:
                self.notify('report_build_failure')
                self.operations.reset()
        return fn

    def test(self):
        """Executes the tests."""
        def fn():
            self.notify('session_start', 'test')
            results = self.executor.test(self.watcher.testlist())
            self.notify('report_results', results)

            if results['total_failed'] == 0 and self.last_failed > 0:
                self.last_failed = 0
                self.operations.append(self.test())
            self.last_failed = results['total_failed']
        return fn

    def run(self, **kwargs):
        """The main polling loop of the monitor."""
        step_mode = first_value(kwargs.get('step'), False)
        while self.runstate.active():
            self.check_for_changes()
            self.wait()

            if step_mode:
                break

    def check_for_changes(self):
        """The work side of the polling.

        If there were changes, then executes the base set of operations.
        """
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
        """The wait side of the polling."""
        try:
            self.notify('wait')
            time.sleep(self.polling_interval)
        except KeyboardInterrupt:
            self.notify('interrupt_detected')
            self.executor.clear_filter()
            self.verify_stop()

    def verify_stop(self):
        """Verify that the user's interrupt was intended to terminate ttt by
        waiting for another interrupt."""
        try:
            time.sleep(self.polling_interval)
            self.runstate.allow_once()
        except KeyboardInterrupt:
            self.notify('halt')
            self.runstate.stop()


class Runstate(object):
    """Tracks the run state of a test session to support KeyboardInterrupt
    control of the current session."""
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
    """Maintains the set of operations scheduled to run in the test session."""
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
    """Get the first value that is not None in the argument list, other use the
    given default.

      >>> first_value(None, 123)
      123
      >>> a = { 'hello': 234 }
      >>> first_value(a['hello'], 123)
      234
    """
    return next(itertools.dropwhile(lambda x: x is None, args), None)
