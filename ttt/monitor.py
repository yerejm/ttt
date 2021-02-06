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
import platform
import subprocess
import sys
import time
import shutil
from timeit import default_timer as timer

from ttt.builder import create_builder
from ttt.watcher import Watcher, has_changes
from ttt.executor import Executor
from ttt.terminal import TerminalReporter, Terminal
from ttt.ircclient import IRCReporter, IRCClient


DEFAULT_BUILD_PATH_SUFFIX = '-build'
DEFAULT_SOURCE_PATTERNS = [
    '*.cc',
    '*.c',
    '*.h',
    'CMakeLists.txt',
]


def create_monitor(watch_path=None, patterns=None, **kwargs):
    """Creates a monitor and its subordinate objects.

    By default, one reporter object is created to output to the terminal.
    An optional IRC reporter may be created if irc_server is provided.

    :param watch_path: (optional) the root of the source tree, either relative
        or absolute. If not provided, the current working directory is assumed
        to be the root of the source tree.
    :param patterns: (optional) a list of file names or patterns that identify
        the files to be tracked. By default, all files are tracked unless this
        list is specified and not empty.
    :param build_path: (optional) the desired build path. May be relative. If
        not provided, it will be generated from the watch path.
    :param generator: (optional) the cmake build system generator
    :param defines: (optional) list of var=val strings for CMake's -D option
    :param irc_server: (optional) the IRC server host if an IRC reporter is
        required.
    :param irc_port (optional) the IRC server port. Has no meaning without
        irc_server.
    :param irc_channel (optional) the IRC channel to join once connected. Has
        no meaning without irc_server.
    :param irc_nick (optional) the IRC nickname to use once connected. Has
        no meaning without irc_server.
    """
    build_config = kwargs.pop("config", None)
    generator = kwargs.pop("generator", None)
    watch_path = make_watch_path(watch_path)
    build_path = make_build_path(kwargs.pop('build_path', None),
                                 watch_path,
                                 build_config)
    if kwargs.pop("clean", False) and os.path.exists(build_path):
        shutil.rmtree(build_path)
    term = Terminal(stream=sys.stdout)
    exclusions = kwargs.pop("exclude", [])
    watcher = Watcher(watch_path, build_path, patterns, exclusions, term)

    run_tests = kwargs.pop("test", False)
    defines = kwargs.pop("define", [])
    if run_tests:
        if defines is None:
            defines = []
        defines.append('ENABLE_TESTS=ON')
    builder = create_builder(
            watch_path,
            build_path,
            generator,
            build_config,
            defines,
            term
        )

    reporters = [TerminalReporter(watch_path, build_path)]

    irc_server = kwargs.pop("irc_server", None)
    if irc_server:
        irc = IRCClient(
            (kwargs.pop('irc_channel', None) or
                '#ttt-{}'.format(os.path.basename(watch_path))),
            (kwargs.pop('irc_nick', None) or
                '{}_{}'.format(platform.system(), build_config)),
            irc_server,
            kwargs.pop("irc_port", None)
        )
        # print('{}@{}:{}/{}'.format(
        #     irc._nickname, irc.server.host, irc.server.port, irc.channel)
        # )
        r = IRCReporter(irc)
        reporters.append(r)

    executor = Executor() if run_tests else None
    return Monitor(watcher, builder, executor, reporters)


def make_watch_path(watch_path=None):
    if watch_path is None:
        watch_path = os.getcwd()
    watch_abspath = os.path.abspath(watch_path)
    if not os.path.exists(watch_abspath):
        import errno
        raise IOError(
            errno.ENOENT,
            "Invalid path: {} ({})".format(watch_abspath, watch_path)
        )
    return watch_abspath


def make_build_path(build_path,
                    watch_path=None,
                    build_type=None,
                    suffix=DEFAULT_BUILD_PATH_SUFFIX):
    """Creates a absolute build path.

    If the build path is given, returns the absolute version.

    If the build path is None, then an absolute path will be created. It will
    be rooted in the current working directory with a name derived from the
    combination of the watch_path, the build_type, and the suffix.

    >>> os.path.basename(make_build_path('build'))
    build-build
    >>> os.path.basename(make_build_path('build', 'watch'))
    build-build
    >>> os.path.basename(make_build_path(None, 'watch'))
    watch-build
    >>> os.path.basename(make_build_path(None, 'watch', 'debug'))
    watch-debug-build
    >>> os.path.basename(make_build_path(None, None, 'debug'))
    debug-build
    >>> os.path.basename(make_build_path(None))
    build

    :param build_path: the build path
    :param watch_path: (optional) the watch path from which the build path is
    derived
    :param build_type: (optional) the build type e.g. debug, release
    :param suffix: (optional) the suffix to append to the watch path. Defaults
    to -build
    :return the absolute build path
    """
    if not build_path:
        build_path = os.path.join(
            os.getcwd(),
            "{}{}{}".format(os.path.basename(watch_path),
                            '' if build_type is None else ('-' + build_type),
                            suffix)
        )
    return os.path.abspath(build_path)


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
        self.notify('session_start', 'build')
        self.notify('report_build_path')
        try:
            start = timer()
            self.builder()
            end = timer()
        except KeyboardInterrupt as e:
            raise e
        except subprocess.CalledProcessError:
            end = timer()
            self.notify('report_build_failure')
            self.operations.reset()
        self.notify('session_end', 'build', end - start)

    def test(self):
        """Executes the tests."""
        if self.executor is None:
            return
        self.notify('session_start', 'test')
        results = self.executor.test(self.watcher.testlist())
        self.notify('report_results', results)
        self.notify('session_end', 'test')

        if results['total_failed'] == 0 and self.last_failed > 0:
            self.last_failed = 0
            self.operations.append(self.test)
        self.last_failed = results['total_failed']

    def run(self, **kwargs):
        """The main polling loop of the monitor."""
        step_mode = first_value(kwargs.get('step'), False)
        while self.runstate.active():
            try:
                self.check_for_changes()
                self.wait()
            except KeyboardInterrupt:
                self.notify('interrupt_detected')
                if self.executor is not None:
                    self.executor.clear_filter()
                self.verify_stop()

            if step_mode:
                break

    def check_for_changes(self):
        """The work side of the polling.

        If there were changes, then executes the base set of operations.
        """
        watchstate = self.watcher.poll()
        if has_changes(watchstate) or self.runstate.allowed_once():
            self.operations.append(
                self.report_change(watchstate),
                self.build,
                self.test
            )
            self.operations.run()
            self.notify('wait_change')

    def wait(self):
        """The wait side of the polling."""
        self.notify('wait')
        time.sleep(self.polling_interval)

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
