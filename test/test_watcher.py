#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
test_watcher
----------------------------------

Tests for `watcher` module.
"""

import os
import re
from testfixtures import TempDirectory
from ttt.watcher import WatchedFile
from ttt.watcher import create_watchstate
from ttt.watcher import Watcher

class TestWatcher:
    def setup(self):
        pass

    def teardown(self):
        TempDirectory.cleanup_all()

    def test_default_watcher(self):
        work_directory = TempDirectory()
        work_directory.write('a.h', b'')
        work_directory.write('a.c', b'')
        work_directory.write('a.cc', b'')
        work_directory.write('CMakeLists.txt', b'')
        work_directory.write('blah.txt', b'')
        w = Watcher(work_directory.path)

        filelist = w.filelist
        assert set([ filelist[f].filename for f in filelist ]) == set(['a.h', 'a.c', 'a.cc', 'CMakeLists.txt'])

    def test_custom_watcher(self):
        work_directory = TempDirectory()
        work_directory.write('a.h', b'')
        work_directory.write('a.c', b'')
        work_directory.write('a.cc', b'')
        work_directory.write('CMakeLists.txt', b'')
        work_directory.write('blah.txt', b'')
        w = Watcher(work_directory.path, ['CMakeLists.txt'])

        filelist = w.filelist
        assert [ filelist[f].filename for f in filelist ] == ['CMakeLists.txt']

    def test_poll(self):
        work_directory = TempDirectory()
        work_directory.write('a.h', b'')
        work_directory.write('a.c', b'')
        work_directory.write('a.cc', b'')
        work_directory.write('CMakeLists.txt', b'')
        work_directory.write('blah.txt', b'')
        w = Watcher(work_directory.path)

        assert not w.poll().has_changed()

        work_directory.write('b.c', b'')
        assert w.poll().has_changed()

class TestWatchState:
    def test_create(self):
        ws = create_watchstate(dict(), dict())

        assert not ws.has_changed()
        assert ws.has_changed() == set()

    def test_equality(self):
        before = { 'test': WatchedFile(filename='test', mtime=1) }
        after = { 'test': WatchedFile(filename='test', mtime=1) }

        ws1 = create_watchstate(before, after)
        ws2 = create_watchstate(dict(), dict())
        assert ws1 == ws2

        ws1 = create_watchstate(before, after)
        ws2 = create_watchstate(before, dict())
        assert ws1 != ws2

        ws1 = create_watchstate(before, after)
        ws2 = create_watchstate(dict(), after)
        assert ws1 != ws2

        ws1 = create_watchstate(before, after)
        ws2 = create_watchstate(before, after)
        assert ws1 == ws2

    def test_unchanged_watchstate(self):
        before = dict()
        before['test'] = WatchedFile(filename='test', mtime=1)
        after = dict()
        after['test'] = WatchedFile(filename='test', mtime=1)

        ws = create_watchstate(before, after)

        assert not ws.has_changed()
        assert ws.has_changed() == set()

    def test_addition_watchstate(self):
        before = dict()
        after = dict()
        after['test'] = WatchedFile(filename='test', mtime=1)

        ws = create_watchstate(before, after)
        assert ws.has_changed()
        assert ws.has_changed() == set(['test'])

    def test_modification_watchstate(self):
        before = dict()
        before['test'] = WatchedFile(filename='test', mtime=1)
        after = dict()
        after['test'] = WatchedFile(filename='test', mtime=2)

        ws = create_watchstate(before, after)
        assert ws.has_changed()
        assert ws.has_changed() == set(['test'])

    def test_deletion_watchstate(self):
        before = dict()
        before['test'] = WatchedFile(filename='test', mtime=1)
        after = dict()

        ws = create_watchstate(before, after)
        assert ws.has_changed()
        assert ws.has_changed() == set(['test'])

