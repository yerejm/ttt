import re
import os
import platform

class WatchedFile(object):
    def __init__(self, root_directory='', relative_directory='', filename='', mtime=0):
        self._root = root_directory
        self._relative = relative_directory
        self._filename = filename
        self._mtime = mtime
    def name(self):
        return self._filename
    def relativepath(self):
        return os.path.join(self._relative, self.name())
    def absolutepath(self):
        return os.path.join(self._root, self._relative, self.name())
    def last_modified(self):
        return self._mtime

class WatchState(object):
    def __init__(self, inserts, deletes, updates):
        self.inserts = inserts
        self.deletes = deletes
        self.updates = updates

    def has_changed(self):
        return self.inserts or self.deletes or self.updates

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

class Watcher(object):
    EXE_SUFFIX = ".exe" if platform.system() == 'Windows' else ""
    DEFAULT_SOURCE_PATTERNS = [
        '\.cc$',
        '\.c$',
        '\.h$',
        'CMakeLists.txt$',
    ]
    DEFAULT_TEST_PREFIX = 'test_'

    """
    Watch the file system for changes.
    This could be additions, deletions, or modifications.
    """
    def __init__(self, context,
            source_patterns=DEFAULT_SOURCE_PATTERNS,
            test_prefix=DEFAULT_TEST_PREFIX):
        self.context = context
        self.source_patterns = [ re.compile(pattern) for pattern in source_patterns ]
        self.test_prefix = test_prefix
        self.filelist = {}

    def poll(self, watch_path):
        current_filelist = get_watched_files(self.context, watch_path, self.source_patterns)
        watchstate = create_watchstate(self.filelist, current_filelist)
        self.filelist = current_filelist
        return watchstate

    def testlist(self):
        """
        Derive from source files a dictionary of the associated expected test file
        names.  The dictionary has keys of expected test file names, and values of
        paths to the associated test source file relative to the watched directory.
        """
        testfiles = dict()
        for filepath, watchedfile in self.filelist.items():
            source_file = watchedfile.name()
            if source_file.startswith(self.test_prefix):
                test_file = source_file[:source_file.rfind('.')] + Watcher.EXE_SUFFIX
                testfiles[test_file] = watchedfile.relativepath()
        return testfiles

def is_watchable(filename, patterns):
    for pattern in patterns:
        if pattern.search(filename):
            return True
    return False

def get_watched_files(context, root_directory, patterns):
    files = dict()
    rootdir_end_index = len(root_directory) + 1
    for dirpath, filename, _ in context.walk(root_directory):
        if is_watchable(filename, patterns):
            watched_file = os.path.join(dirpath, filename)
            files[watched_file] = WatchedFile(
                    root_directory,
                    dirpath[rootdir_end_index:],
                    filename,
                    os.path.getmtime(watched_file)
                )
    return files

def create_watchstate(dictA, dictB):
    dictAKeys = set(dictA.keys())
    dictBKeys = set(dictB.keys())
    inserts = dictBKeys - dictAKeys
    deletes = dictAKeys - dictBKeys
    updates = set()
    for filename in dictA.keys():
        if filename in dictB and dictB[filename].last_modified() != dictA[filename].last_modified():
            updates.add(filename)
    return WatchState(inserts, deletes, updates)

