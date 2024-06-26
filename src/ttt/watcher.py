"""
ttt.watcher
~~~~~~~~~~~~
This module implements the watcher. It "watches" a source tree for changes,
and identifies tests associated with those files that changed.

The watching follows the polling paradigm: by walking the directory tree from
a root and checking the modified time of each file found in the traversal.
Polling was the best general solution for multiple platforms because the main
use case of the watcher is to watch files on a shared network drive. The native
file system event APIs do not emit events for changes to files on a network
drive.

Polling does result in a pulse of CPU activity and this may become unusable on
large source trees or if there are multiple instances of ttt running. This
potential issue is left to a time when it becomes problematic.

:copyright: (c) yerejm
"""

import collections
import os
from os import walk as walk_fn
import platform
import re
import stat

try:
    from timeit import default_timer as timer
except ImportError:
    # Pick the better resolution timer for the platform
    if platform.system() == "Windows":
        from time import clock as timer
    else:
        from time import time as timer

from ttt.gtest import GTest

DEFAULT_TEST_PREFIX = "test_"

# When traversing a directory tree, do not enter the following directories
EXCLUSIONS = set([".git", ".hg"])

EXE_SUFFIX = ".exe" if platform.system() == "Windows" else ""


WatchState = collections.namedtuple(
    "WatchState", ["inserts", "deletes", "updates", "walk_time"]
)


WatchedFile = collections.namedtuple("WatchedFile", ["name", "relpath", "mtime"])


class Watcher(object):
    """Tracks the state of files under a directory tree known as the watch path.

    The Watcher maintains a dict of WatchFile objects for each file that will
    be tracked.

    :param watch_path: the absolute path to the root of the directory tree
        where the modification times of all files under it are tracked.
    :param build_path: the absolute path to the root of the directory tree
        where the build artifacts derived from the files in the watch area are
        located.
    :param source_patterns: (optional) a list of file names or patterns that
        identify the files to be tracked. By default, all files are tracked
        unless this list is specified and not empty.
    :param source_exclusions: (optional) a list of file names or patterns that
        identify the files to be ignored.
    :param term: (optional) output stream for verbose output
    """

    def __init__(
        self,
        watch_path,
        build_path,
        source_patterns=None,
        source_exclusions=None,
        term=None,
    ):
        if source_patterns is None:
            source_patterns = []  # get everything by default
        if source_exclusions is None:
            source_exclusions = []
        self.watch_path = watch_path
        self.build_path = build_path
        self.source_patterns = compile_patterns(source_patterns)
        self.source_exclusions = compile_patterns(source_exclusions)
        self.term = term

        # The file list will be a dict of absolute source file paths to
        # WatchedFile objects.
        self.filelist = {}

    def poll(self):
        """Traverses the watch area to refresh the dictionary of tracked files.

        Exclusion is applied before inclusion.

        Certain subdirectories detected during traversal are skipped entirely.
        This list is currently limited to the git and mercurial repository
        meta-areas.

        :return WatchState object identifying the file activity under the watch
        area i.e. whether there are new files, changed files, deleted files.
        """

        def include_file(filename, inclusion_patterns, exclusion_patterns):
            for pattern in exclusion_patterns:
                if pattern.search(filename):
                    return False

            if not inclusion_patterns:
                return True

            for pattern in inclusion_patterns:
                if pattern.search(filename):
                    return True
            return False

        rootdir_end_index = len(self.watch_path) + 1
        with Timer() as t:
            current_filelist = {
                os.path.join(d, f): WatchedFile(
                    f, os.path.join(d[rootdir_end_index:], f), t
                )
                for d, f, _, t in walk(self.watch_path, EXCLUSIONS)
                if include_file(
                    os.path.join(d, f), self.source_patterns, self.source_exclusions
                )
            }
        watchstate = create_watchstate(self.filelist, current_filelist, t.secs)
        self.filelist = current_filelist
        return watchstate

    def testlist(self, test_prefix=DEFAULT_TEST_PREFIX):
        """Collects the test files from the source files.

        The files identified as the source files for tests are used to identify
        the test executables in the build area.

        :param test_prefix: (optional) the filename prefix expected to identify
        test source files. By default, this is 'test_'.
        :return list of (absolute executable path, relative source path) tuples
        """
        if self.build_path is None:
            return []

        watchedfiles = self.filelist.values()
        # Create dict of expected test binary names to the relative path of the
        # source files that they were compiled from. This is to make
        # identification of test binaries easier during build tree scanning.
        # NOTE: On Windows, executables can be identified by %PATHEXT% but
        # this assumes gtest builds will always create exe.
        testfiles = {
            os.path.splitext(w.name)[0] + EXE_SUFFIX: w.relpath
            for w in watchedfiles
            if w.name.startswith(test_prefix)
        }
        # Scan the build tree. If an expected test binary is encountered, add a
        # GTest().
        return [
            GTest(testfiles[f], os.path.join(d, f), term=self.term)
            for d, f, m, t in walk(self.build_path)
            if f in testfiles and m & stat.S_IXUSR
        ]


def create_watchstate(dictA, dictB, walk_time=0):
    """Creates sets of differences between two watch path states.

    :param dictA: Old dict of files from the watch area
    :param dictB: New dict of files from the watch area
    :param walk_time: (optional) The time in seconds to traverse the watch area
    """
    dictA = {} if dictA is None else dictA
    dictB = {} if dictB is None else dictB
    dictAKeys = set(dictA.keys())
    dictBKeys = set(dictB.keys())
    return WatchState(
        inserts=dictBKeys - dictAKeys,
        deletes=dictAKeys - dictBKeys,
        updates=set(
            [f for f in dictA.keys() if f in dictB and dictB[f].mtime != dictA[f].mtime]
        ),
        walk_time=walk_time,
    )


def has_changes(watch_state):
    """Indicates whether the watch state contains file level activity."""
    return watch_state.inserts or watch_state.updates or watch_state.deletes


def walk(root_directory, exclusions=None):
    """Traverse the directory structure under a given root directory, yielding
    the details of each file found.

    Details yielded are:
      - The path to the file
      - The file name
      - The file permissions
      - The file last modified time

    This is mostly a wrapper around python's walk to try to use the better
    performing version for the python in use.

    :param root_directory: the directory from which to start traversal
    :param exclusions: (optional) a set of names that traversal will skip. For
    example, a directory name identifying a subdirectory whose own traversal is
    not required.
    """
    if exclusions is None:
        exclusions = set()
    for dirpath, dirlist, filelist in walk_fn(root_directory, topdown=True):
        dirlist[:] = [d for d in dirlist if d not in exclusions]
        for filename in filelist:
            path = os.path.join(dirpath, filename)
            try:
                filestat = os.stat(path)
                if stat.S_ISREG(filestat.st_mode):
                    yield (
                        dirpath,
                        filename,
                        filestat.st_mode,  # file permissions
                        filestat.st_mtime,  # last modified time
                    )
            except OSError:
                # probably FileNotFoundError, but OSError on Windows
                continue


def compile_patterns(pattern_list):
    return [
        re.compile(re.escape(p).replace("\\?", ".").replace("\\*", ".*?"))
        for p in pattern_list
    ]


class Timer(object):
    """Self-capturing time keeper intended for use by the 'with' idiom."""

    def __enter__(self):
        self.start = timer()
        return self

    def __exit__(self, *args):
        self.end = timer()
        self.secs = self.end - self.start
