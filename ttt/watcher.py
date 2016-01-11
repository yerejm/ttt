import collections
import re
import os
import platform
import errno

from ttt import systemcontext

DEFAULT_TEST_PREFIX = 'test_'
DEFAULT_SOURCE_PATTERNS = [
    '\.cc$',
    '\.c$',
    '\.h$',
    'CMakeLists.txt$',
]
EXE_SUFFIX = ".exe" if platform.system() == 'Windows' else ""


WatchState = collections.namedtuple(
    'WatchState',
    ['inserts', 'deletes', 'updates', 'walk_time']
)


WatchedFile = collections.namedtuple(
    'WatchedFile',
    ['name', 'relpath', 'mtime']
)


class Watcher(object):
    """Maintains a dictionary of files under the watched path."""
    def __init__(self,
                 context,
                 watch_path,
                 source_patterns=DEFAULT_SOURCE_PATTERNS):
        self.watch_path = watch_path
        self.context = context
        self.source_patterns = [re.compile(p) for p in source_patterns]
        self.filelist = {}

    def poll(self):
        """Walk the file system to refresh the dictionary of files.
        Returns a WatchState of changes (inserts, updates, deletes)."""
        rootdir_end_index = len(self.watch_path) + 1
        with systemcontext.Timer() as t:
            current_filelist = {
                os.path.join(d, f):
                    WatchedFile(f, os.path.join(d[rootdir_end_index:], f), t)
                for pattern in self.source_patterns
                for d, f, _, t in self.context.walk(self.watch_path)
                if pattern.search(f)
            }
        watchstate = create_watchstate(self.filelist, current_filelist, t.secs)
        self.filelist = current_filelist
        return watchstate


def watch(context, watch_path, **kwargs):
    """Watch the given path for changes. Returns a Watcher."""
    full_watch_path = os.path.abspath(watch_path)
    if not os.path.exists(full_watch_path):
        raise IOError(
            errno.ENOENT,
            "Invalid path: {} ({})".format(watch_path, full_watch_path)
        )
    return Watcher(context, full_watch_path, **kwargs)


def derive_tests(watched_files, test_prefix=DEFAULT_TEST_PREFIX):
    """Derive the expected test files from the source files."""
    return {
        os.path.splitext(w.name)[0] + EXE_SUFFIX: w.relpath
        for w in watched_files if w.name.startswith(test_prefix)
    }


def create_watchstate(dictA={}, dictB={}, walk_time=0):
    """Creates sets of differences between two watch path states."""
    dictAKeys = set(dictA.keys())
    dictBKeys = set(dictB.keys())
    return WatchState(
        inserts=dictBKeys - dictAKeys,
        deletes=dictAKeys - dictBKeys,
        updates=set([
            f
            for f in dictA.keys()
            if f in dictB and dictB[f].mtime != dictA[f].mtime
        ]),
        walk_time=walk_time
    )


def has_changes(watch_state):
    """Indicates whether the watch state contains file changes."""
    return watch_state.inserts or watch_state.updates or watch_state.deletes
