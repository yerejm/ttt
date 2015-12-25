#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
test_systemcontext
----------------------------------

Tests for `systemcontext` module.
"""
import os
from testfixtures import TempDirectory

from ttt.systemcontext import SystemContext

class TestSystemContext:
    def setup(self):
        pass

    def teardown(self):
        TempDirectory.cleanup_all()

    def test_file_system(self):
        wd = TempDirectory()
        wd.write('test1.txt', b'')
        wd.write('test2.txt', b'')
        wd.makedir('test');
        wd.write(['test', 'test3.txt'], b'')
        fs = SystemContext(wd.path)

        wdpathlen = len(wd.path) + 1
        paths = [ os.path.join(d[wdpathlen:], f) for d, f, m in fs.walk() ]
        assert paths == [ 'test1.txt', 'test2.txt', 'test/test3.txt' ]

