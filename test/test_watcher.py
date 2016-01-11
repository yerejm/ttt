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
from ttt import watcher
from ttt.watcher import Watcher
from ttt.watcher import WatchedFile
from ttt.watcher import create_watchstate
from ttt.watcher import watch
from ttt.systemcontext import SystemContext

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

        sc = SystemContext()
        w = watch(sc, work_directory.path)
        w.poll()

        filelist = w.filelist
        assert set([ filelist[f].name for f in filelist ]) == set(['a.h', 'a.c', 'a.cc', 'CMakeLists.txt'])

    def test_custom_watcher(self):
        work_directory = TempDirectory()
        work_directory.write('a.h', b'')
        work_directory.write('a.c', b'')
        work_directory.write('a.cc', b'')
        work_directory.write('CMakeLists.txt', b'')
        work_directory.write('blah.txt', b'')

        sc = SystemContext()
        w = watch(sc, work_directory.path, source_patterns=['CMakeLists.txt'])
        w.poll()

        filelist = w.filelist
        assert [ filelist[f].name for f in filelist ] == ['CMakeLists.txt']

    def test_poll(self):
        work_directory = TempDirectory()
        work_directory.write('a.h', b'')
        work_directory.write('a.c', b'')
        work_directory.write('a.cc', b'')
        work_directory.write('CMakeLists.txt', b'')
        work_directory.write('blah.txt', b'')

        sc = SystemContext()
        w = watch(sc, work_directory.path)

        watchstate = w.poll()
        assert watcher.has_changes(watchstate)

        watchstate = w.poll()
        assert not watcher.has_changes(watchstate)

        work_directory.write('b.c', b'')
        watchstate = w.poll()
        assert watcher.has_changes(watchstate)

    def test_derive_tests(self):
        work_directory = TempDirectory()
        work_directory.makedir('test')
        testfile_path = work_directory.write(['test', 'test_dummy.c'], b'')

        sc = SystemContext()
        w = watch(sc, work_directory.path)
        w.poll()

        exefile = 'test_dummy' + watcher.EXE_SUFFIX
        assert(watcher.derive_tests(w.filelist.values()) ==
                { exefile: os.path.join('test', 'test_dummy.c') })

class TestWatchState:
    def test_create(self):
        ws = create_watchstate(dict(), dict())

        assert not watcher.has_changes(ws)

    def test_equality(self):
        before = { 'test': WatchedFile(relpath='', name='', mtime='') }
        after = { 'test': WatchedFile(relpath='', name='', mtime='') }

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
        before['test'] = WatchedFile(relpath='', name='', mtime='')
        after = dict()
        after['test'] = WatchedFile(relpath='', name='', mtime='')

        ws = create_watchstate(before, after)

        assert not watcher.has_changes(ws)

    def test_addition_watchstate(self):
        before = dict()
        after = dict()
        after['test'] = WatchedFile(relpath='', name='', mtime='')

        ws = create_watchstate(before, after)
        assert ws.inserts == set(['test'])
        assert not ws.updates
        assert not ws.deletes

    def test_modification_watchstate(self):
        before = dict()
        before['test'] = WatchedFile(relpath='', name='', mtime=1)
        after = dict()
        after['test'] = WatchedFile(relpath='', name='', mtime=2)

        ws = create_watchstate(before, after)
        assert ws.updates == set(['test'])
        assert not ws.inserts
        assert not ws.deletes

    def test_deletion_watchstate(self):
        before = dict()
        before['test'] = WatchedFile(relpath='', name='', mtime='')
        after = dict()

        ws = create_watchstate(before, after)
        assert ws.deletes == set(['test'])
        assert not ws.updates
        assert not ws.inserts
