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
from ttt.watcher import Watcher
from ttt.watcher import WatchedFile
from ttt.watcher import create_watchstate
from ttt.watcher import create_watcher
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
        w = create_watcher(sc, work_directory.path)
        w.poll()

        filelist = w.filelist()
        assert set([ filelist[f].name() for f in filelist ]) == set(['a.h', 'a.c', 'a.cc', 'CMakeLists.txt'])

    def test_custom_watcher(self):
        work_directory = TempDirectory()
        work_directory.write('a.h', b'')
        work_directory.write('a.c', b'')
        work_directory.write('a.cc', b'')
        work_directory.write('CMakeLists.txt', b'')
        work_directory.write('blah.txt', b'')

        sc = SystemContext()
        w = create_watcher(sc, work_directory.path, source_patterns=['CMakeLists.txt'])
        w.poll()

        filelist = w.filelist()
        assert [ filelist[f].name() for f in filelist ] == ['CMakeLists.txt']

    def test_poll(self):
        work_directory = TempDirectory()
        work_directory.write('a.h', b'')
        work_directory.write('a.c', b'')
        work_directory.write('a.cc', b'')
        work_directory.write('CMakeLists.txt', b'')
        work_directory.write('blah.txt', b'')

        sc = SystemContext()
        w = create_watcher(sc, work_directory.path)

        watchstate = w.poll()
        assert watchstate.has_changed()

        watchstate = w.poll()
        assert not watchstate.has_changed()

        work_directory.write('b.c', b'')
        watchstate = w.poll()
        assert watchstate.has_changed()

    def test_testdict(self):
        work_directory = TempDirectory()
        work_directory.makedir('test')
        testfile_path = work_directory.write(['test', 'test_dummy.c'], b'')

        sc = SystemContext()
        w = create_watcher(sc, work_directory.path)
        w.poll()

        exefile = 'test_dummy' + Watcher.EXE_SUFFIX
        assert w.testdict() == { exefile: os.path.join('test', 'test_dummy.c') }

class TestWatchState:
    def test_create(self):
        ws = create_watchstate(dict(), dict())

        assert not ws.has_changed()
        assert ws.has_changed() == set()

    def test_equality(self):
        before = { 'test': WatchedFile() }
        after = { 'test': WatchedFile() }

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
        before['test'] = WatchedFile()
        after = dict()
        after['test'] = WatchedFile()

        ws = create_watchstate(before, after)

        assert not ws.has_changed()
        assert ws.has_changed() == set()

    def test_addition_watchstate(self):
        before = dict()
        after = dict()
        after['test'] = WatchedFile()

        ws = create_watchstate(before, after)
        assert ws.has_changed()
        assert ws.has_changed() == set(['test'])

    def test_modification_watchstate(self):
        before = dict()
        before['test'] = WatchedFile('', '', '', 1)
        after = dict()
        after['test'] = WatchedFile('', '', '', 2)

        ws = create_watchstate(before, after)
        assert ws.has_changed()
        assert ws.has_changed() == set(['test'])

    def test_deletion_watchstate(self):
        before = dict()
        before['test'] = WatchedFile()
        after = dict()

        ws = create_watchstate(before, after)
        assert ws.has_changed()
        assert ws.has_changed() == set(['test'])

    def test_str(self):
        ws = create_watchstate()
        assert str(ws) == "WatchState(0 inserted, 0 deleted, 0 modified)"

    def test_repr(self):
        empty_list = repr(set([]))
        ws = create_watchstate()
        assert repr(ws) == "WatchState({empty}, {empty}, {empty})".format(empty=empty_list)

