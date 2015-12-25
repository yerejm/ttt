#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
test_executor
----------------------------------

Tests for `executor` module.
"""
import os
import re
import io
import sys
import stat

from testfixtures import TempDirectory
from contextlib import contextmanager

from ttt.executor import Executor
from ttt.executor import BuildFile
from ttt.executor import FileProvider

def starts_with_test(filename):
    return filename.startswith('test')

@contextmanager
def stdout_redirector(stream):
    old_stdout = sys.stdout
    sys.stdout = stream
    try:
        yield
    finally:
        sys.stdout = old_stdout

class MockProcess:
    def __init__(self, output):
        self.output = output
        self.command = None

    def streamed_call(self, command, listener):
        self.command = command
        for line in self.output:
            listener(line)

class TestExecutor:
    pass

class TestProvider:
    def test_provider(self):
        bf1 = ('/path/to', 'test_dummy', stat.S_IXUSR)
        bf2 = ('/path/to', 'dummy.c', stat.S_IRUSR)
        bf3 = ('/path/to', 'test_dummy.c', stat.S_IRUSR)
        filelist = [ bf1, bf2, bf3 ]

        class FileSystem(object):
            def walk(self):
                for t in filelist:
                    yield t

        fs = FileSystem()
        provider = FileProvider(fs)
        t = [ f for f in provider.glob_files(starts_with_test) ]

        assert t == [ BuildFile(*bf1), BuildFile(*bf3) ]

# class TestExecutor:
#     def test_executor(self):
#         bf1 = BuildFile('test_dummy', '/path/to/test_dummy', stat.S_IXUSR)
#         bf2 = BuildFile('dummy.c', '/path/to/dummy.c', stat.S_IRUSR)
#         bf3 = BuildFile('test_dummy.c', '/path/to/test_dummy.c', stat.S_IRUSR)
#
#         fs = MockFileSystem([ bf1, bf2, bf3 ])
#         provider = FileProvider(fs)
#         e = Executor(provider)
#
#         filelist = {
#             'dummy.c': TestFile(prefix='test_', testname='dummy', filename='test_dummy')
#         }
#         assert e.test(filelist) == []

