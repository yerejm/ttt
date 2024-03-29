#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
test_watcher
----------------------------------

Tests for `watcher` module.
"""

import os

from testfixtures import TempDirectory

from ttt import watcher
from ttt.watcher import create_watchstate, WatchedFile, Watcher


class TestWatcher:
    def setup_method(self):
        pass

    def teardown_method(self):
        TempDirectory.cleanup_all()

    def test_default_watcher_gets_all_files(self):
        work_directory = TempDirectory()
        work_directory.write("a.h", b"")
        work_directory.write("a.c", b"")
        work_directory.write("a.cc", b"")
        work_directory.write("CMakeLists.txt", b"")
        work_directory.write("blah.txt", b"")
        work_directory.makedir(".git")
        work_directory.makedir(".hg")
        wd_len = len(work_directory.path) + 1

        w = Watcher(work_directory.path, None)
        watchstate = w.poll()
        filelist = [f[wd_len:] for f in watchstate.inserts]
        filelist.sort()
        assert filelist == ["CMakeLists.txt", "a.c", "a.cc", "a.h", "blah.txt"]

    def test_watcher_with_file_filter(self):
        work_directory = TempDirectory()
        work_directory.write("a.h", b"")
        work_directory.write("a.c", b"")
        work_directory.write("a.cc", b"")
        work_directory.write("CMakeLists.txt", b"")
        work_directory.write("blah.txt", b"")
        blah_directory = work_directory.makedir("blah")
        work_directory.write((blah_directory, "test_dummy.c"), b"")
        wd_len = len(work_directory.path) + 1

        w = Watcher(work_directory.path, None, [])
        watchstate = w.poll()
        filelist = [f[wd_len:] for f in watchstate.inserts]
        filelist.sort()
        assert filelist == [
            "CMakeLists.txt",
            "a.c",
            "a.cc",
            "a.h",
            "blah.txt",
            os.path.join("blah", "test_dummy.c"),
        ]

        w = Watcher(work_directory.path, None, source_patterns=["CMakeLists.txt"])
        watchstate = w.poll()
        filelist = [f[wd_len:] for f in watchstate.inserts]
        filelist.sort()
        assert filelist == ["CMakeLists.txt"]

        w = Watcher(work_directory.path, None, source_patterns=["*.txt"])
        watchstate = w.poll()
        filelist = [f[wd_len:] for f in watchstate.inserts]
        filelist.sort()
        assert filelist == ["CMakeLists.txt", "blah.txt"]

        w = Watcher(work_directory.path, None, source_patterns=["?.cc"])
        watchstate = w.poll()
        filelist = [f[wd_len:] for f in watchstate.inserts]
        filelist.sort()
        assert filelist == ["a.cc"]

        w = Watcher(work_directory.path, None, source_patterns=["blah"])
        watchstate = w.poll()
        filelist = [f[wd_len:] for f in watchstate.inserts]
        filelist.sort()
        assert filelist == ["blah.txt", os.path.join("blah", "test_dummy.c")]

        w = Watcher(work_directory.path, None, source_patterns=["blah" + os.sep])
        watchstate = w.poll()
        filelist = [f[wd_len:] for f in watchstate.inserts]
        filelist.sort()
        assert filelist == [os.path.join("blah", "test_dummy.c")]

        w = Watcher(
            work_directory.path,
            None,
            source_patterns=["*.txt"],
            source_exclusions=["blah.txt"],
        )
        watchstate = w.poll()
        filelist = [f[wd_len:] for f in watchstate.inserts]
        filelist.sort()
        assert filelist == ["CMakeLists.txt"]

        w = Watcher(
            work_directory.path,
            None,
            source_patterns=["*.txt"],
            source_exclusions=["blah.*"],
        )
        watchstate = w.poll()
        filelist = [f[wd_len:] for f in watchstate.inserts]
        filelist.sort()
        assert filelist == ["CMakeLists.txt"]

        w = Watcher(
            work_directory.path, None, None, source_exclusions=["*.txt", "blah"]
        )
        watchstate = w.poll()
        filelist = [f[wd_len:] for f in watchstate.inserts]
        filelist.sort()
        assert filelist == ["a.c", "a.cc", "a.h"]

    def test_poll(self):
        work_directory = TempDirectory()
        work_directory.write("a.h", b"")
        work_directory.write("a.c", b"")
        work_directory.write("a.cc", b"")
        work_directory.write("CMakeLists.txt", b"")
        work_directory.write("blah.txt", b"")

        w = Watcher(work_directory.path, None)

        watchstate = w.poll()
        assert watcher.has_changes(watchstate)

        watchstate = w.poll()
        assert not watcher.has_changes(watchstate)

        work_directory.write("b.c", b"")
        watchstate = w.poll()
        assert watcher.has_changes(watchstate)

    def test_testlist(self):
        import stat

        work_directory = TempDirectory()
        test_directory = work_directory.makedir("test")
        work_directory.write((test_directory, "test_dummy.c"), b"")
        build_directory = TempDirectory()
        testbin_path = build_directory.write("test_dummy" + watcher.EXE_SUFFIX, b"")
        st = os.stat(testbin_path)
        os.chmod(testbin_path, st.st_mode | stat.S_IEXEC)

        w = Watcher(work_directory.path, build_directory.path)
        w.poll()

        testlist = [(g.source(), g.executable()) for g in w.testlist()]
        assert testlist == [
            (
                os.path.join("test", "test_dummy.c"),
                os.path.join(build_directory.path, "test_dummy" + watcher.EXE_SUFFIX),
            )
        ]


class TestWatchState:
    def test_create(self):
        ws = create_watchstate(dict(), dict())

        assert not watcher.has_changes(ws)

    def test_equality(self):
        before = {"test": WatchedFile(relpath="", name="", mtime="")}
        after = {"test": WatchedFile(relpath="", name="", mtime="")}

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
        before["test"] = WatchedFile(relpath="", name="", mtime="")
        after = dict()
        after["test"] = WatchedFile(relpath="", name="", mtime="")

        ws = create_watchstate(before, after)

        assert not watcher.has_changes(ws)

    def test_addition_watchstate(self):
        before = dict()
        after = dict()
        after["test"] = WatchedFile(relpath="", name="", mtime="")

        ws = create_watchstate(before, after)
        assert ws.inserts == set(["test"])
        assert not ws.updates
        assert not ws.deletes

    def test_modification_watchstate(self):
        before = dict()
        before["test"] = WatchedFile(relpath="", name="", mtime=1)
        after = dict()
        after["test"] = WatchedFile(relpath="", name="", mtime=2)

        ws = create_watchstate(before, after)
        assert ws.updates == set(["test"])
        assert not ws.inserts
        assert not ws.deletes

    def test_deletion_watchstate(self):
        before = dict()
        before["test"] = WatchedFile(relpath="", name="", mtime="")
        after = dict()

        ws = create_watchstate(before, after)
        assert ws.deletes == set(["test"])
        assert not ws.updates
        assert not ws.inserts
