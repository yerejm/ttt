import re
import os
import platform
import errno

from ttt import systemcontext


def create_watcher(context, watch_path, **kwargs):
    full_watch_path = os.path.abspath(watch_path)
    if not os.path.exists(full_watch_path):
        raise IOError(
            errno.ENOENT,
            "Invalid path: {} ({})".format(watch_path, full_watch_path)
        )
    return Watcher(context, full_watch_path, **kwargs)


class Watcher(object):
    EXE_SUFFIX = ".exe" if platform.system() == 'Windows' else ""
    DEFAULT_SOURCE_PATTERNS = [
        '\.cc$',
        '\.c$',
        '\.h$',
        'CMakeLists.txt$',
    ]
    DEFAULT_TEST_PREFIX = 'test_'
    CREATED, DELETED, MODIFIED = range(3)

    """
    Watch the file system for changes.
    This could be additions, deletions, or modifications.
    """
    def __init__(self, context, watch_path,
                 source_patterns=DEFAULT_SOURCE_PATTERNS,
                 test_prefix=DEFAULT_TEST_PREFIX):
        self.provider = DefaultFileProvider(
            context, watch_path, source_patterns
        )
        self.test_prefix = test_prefix
        self.watch_path = watch_path

    def poll(self):
        return self.provider.watchstate()

    def filelist(self):
        return self.provider.filelist()

    def testdict(self):
        """
        Derive from source files a dictionary of the associated expected test
        file names.  The dictionary has keys of expected test file names, and
        values of paths to the associated test source file relative to the
        watched directory.
        """
        def is_test_source(x):
            filepath, watchedfile = x
            return watchedfile.name().startswith(self.test_prefix)

        testfiles = dict()
        test_sources = filter(is_test_source, self.provider.filelist().items())
        for filepath, watchedfile in test_sources:
            source_file = watchedfile.name()
            test_file = (
                source_file[:source_file.rfind('.')] + Watcher.EXE_SUFFIX
            )
            testfiles[test_file] = watchedfile.relativepath()
        return testfiles


class DefaultFileProvider(object):
    def __init__(self, context, root_directory, source_patterns):
        self.watch_path = root_directory
        self.context = context
        self.source_patterns = [
            re.compile(pattern) for pattern in source_patterns
        ]
        self._filelist = {}

    def watchstate(self):
        with systemcontext.Timer() as t:
            current_filelist = get_watched_files(
                self.context, self.watch_path, self.source_patterns
            )
        watchstate = create_watchstate(
            self._filelist, current_filelist, t.secs
        )
        self._filelist = current_filelist
        return watchstate

    def filelist(self):
        return self._filelist


def get_watched_files(context, root_directory, patterns):
    def is_watchable(x):
        dirpath, filename, mode = x
        for pattern in patterns:
            if pattern.search(filename):
                return True
        return False

    files = dict()
    rootdir_end_index = len(root_directory) + 1
    for d, f, _ in filter(is_watchable, context.walk(root_directory)):
        watched_file = os.path.join(d, f)
        files[watched_file] = WatchedFile(
            root_directory,
            d[rootdir_end_index:],
            f,
            os.path.getmtime(watched_file)
        )
    return files


class WatchedFile(object):
    def __init__(self, root_directory='', relative_directory='',
                 filename='', mtime=0):
        self._root = root_directory
        self._relative = relative_directory
        self._filename = filename
        self._mtime = mtime

    def name(self):
        return self._filename

    def relativepath(self):
        return os.path.join(self._relative, self.name())

    def last_modified(self):
        return self._mtime


def create_watchstate(dictA={}, dictB={}, walk_time=0):
    dictAKeys = set(dictA.keys())
    dictBKeys = set(dictB.keys())
    inserts = dictBKeys - dictAKeys
    deletes = dictAKeys - dictBKeys
    updates = set()
    for filename in dictA.keys():
        if (filename in dictB and
                dictB[filename].last_modified() !=
                dictA[filename].last_modified()):
            updates.add(filename)
    return WatchState(inserts, deletes, updates, walk_time)


class WatchState(object):
    def __init__(self, inserts=[], deletes=[], updates=[], walk_time=0):
        self.inserts = inserts
        self.deletes = deletes
        self.updates = updates
        self.walk_time = walk_time

    def has_changed(self):
        return self.inserts or self.deletes or self.updates

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def __str__(self):
        return "WatchState({} inserted, {} deleted, {} modified)".format(
            len(self.inserts),
            len(self.deletes),
            len(self.updates)
        )

    def __repr__(self):
        return "WatchState({}, {}, {})".format(
            repr(self.inserts),
            repr(self.deletes),
            repr(self.updates)
        )
