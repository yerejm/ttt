#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
test_systemcontext
----------------------------------

Tests for `systemcontext` module.
"""
import os
import stat
from testfixtures import TempDirectory

from ttt.systemcontext import SystemContext

class TestSystemContext:
    def setup(self):
        self.wd = wd = TempDirectory()
        wd.write('test1.txt', b'')
        wd.write('dummy2.txt', b'')
        wd.makedir('test');
        wd.write(['test', 'test3.txt'], b'')

    def teardown(self):
        TempDirectory.cleanup_all()

    def test_walk(self):
        sc = SystemContext()

        wdpathlen = len(self.wd.path) + 1
        paths = [ os.path.join(d[wdpathlen:], f) for d, f, m in sc.walk(self.wd.path) ]
        assert paths == [ 'dummy2.txt', 'test1.txt', 'test/test3.txt' ]

    def test_glob_files(self):
        sc = SystemContext()

        t = [ f for d, f, m in sc.glob_files(self.wd.path, lambda x: x.startswith('test')) ]

        assert t == [ 'test1.txt', 'test3.txt' ]


