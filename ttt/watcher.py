import re
import os
import collections
import time

DEFAULT_SOURCE_PATTERNS = [
    '\.cc$',
    '\.c$',
    '\.h$',
    'CMakeLists.txt$',
]

WatchedFile = collections.namedtuple(
    "WatchedFile",
    [ "filename", "mtime" ]
)
WatchedFile.__new__.__defaults__ = (None, None)

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
    """
    Watch the file system for changes.
    This could be additions, deletions, or modifications.
    """
    def __init__(self, watch_path, source_patterns=DEFAULT_SOURCE_PATTERNS):
        self.watch_path = watch_path
        self.source_patterns = [ re.compile(pattern) for pattern in source_patterns ]
        self.filelist = get_watched_files(self.watch_path, self.source_patterns)

    def poll(self):
        current_filelist = get_watched_files(self.watch_path, self.source_patterns)
        watchstate = create_watchstate(self.filelist, current_filelist)
        self.filelist = current_filelist
        return watchstate

def is_watchable(filename, patterns):
    for pattern in patterns:
        if pattern.search(filename):
            return True
    return False

def get_watched_files(root_directory, patterns):
    files = dict()
    for dirpath, dirlist, filelist in os.walk(root_directory):
        for filename in filelist:
            if is_watchable(filename, patterns):
                watched_file = os.path.join(dirpath, filename)
                files[watched_file] = WatchedFile(
                    filename=filename,
                    mtime=os.path.getmtime(watched_file)
                )
    return files

def create_watchstate(dictA, dictB):
    dictAKeys = set(dictA.keys())
    dictBKeys = set(dictB.keys())
    inserts = dictBKeys - dictAKeys
    deletes = dictAKeys - dictBKeys
    updates = set()
    for filename in dictA.keys():
        if filename in dictB and dictB[filename].mtime != dictA[filename].mtime:
            updates.add(filename)
    return WatchState(inserts, deletes, updates)

