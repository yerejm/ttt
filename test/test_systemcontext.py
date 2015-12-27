#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
test_systemcontext
----------------------------------

Tests for `systemcontext` module.
"""
import os
import stat
import subprocess

import pytest
from testfixtures import TempDirectory

from ttt.systemcontext import SystemContext

PROGRAM_NAME = 'test.py'
def create_program(exit_code=0):
    program = [ 'import sys', 'print("hello")' ]
    program.append('sys.exit({})'.format(exit_code))
    return os.linesep.join(program).encode('utf-8')

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
        assert paths == [ 'dummy2.txt', 'test1.txt', os.path.join('test', 'test3.txt') ]

    def test_execute(self):
        sc = SystemContext()

        exefile = self.wd.write(PROGRAM_NAME, create_program(exit_code=0))
        command = ['python', exefile]
        output = sc.execute(command, universal_newlines=True)
        assert output == [ 'hello' ]

    def test_execute_error(self):
        sc = SystemContext()

        exefile = self.wd.write(PROGRAM_NAME, create_program(exit_code=1))
        command = ['python', exefile]
        with pytest.raises(subprocess.CalledProcessError):
            sc.execute(command, universal_newlines=True)

    def test_checked_call(self):
        sc = SystemContext()

        exefile = self.wd.write(PROGRAM_NAME, create_program(exit_code=0))
        command = ['python', exefile]
        assert 0 == sc.checked_call(command, universal_newlines=True)

    def test_checked_call_error(self):
        sc = SystemContext()

        exefile = self.wd.write(PROGRAM_NAME, create_program(exit_code=1))
        command = ['python', exefile]
        with pytest.raises(subprocess.CalledProcessError):
            sc.checked_call(command, universal_newlines=True)

    def test_streamed_call(self):
        sc = SystemContext()

        exefile = self.wd.write(PROGRAM_NAME, create_program(exit_code=0))
        command = ['python', exefile]
        assert 0 == sc.streamed_call(command, universal_newlines=True)

    def test_streamed_call_error(self):
        sc = SystemContext()

        exefile = self.wd.write(PROGRAM_NAME, create_program(exit_code=1))
        command = ['python', exefile]
        assert 1 == sc.streamed_call(command, universal_newlines=True)

    def test_streamed_call_with_handler(self):
        output = []
        def line_handler(line):
            output.append(line)
            output.append('boo')

        exefile = self.wd.write(PROGRAM_NAME, create_program(exit_code=0))
        command = ['python', exefile]
        sc = SystemContext()
        rc = sc.streamed_call(command, universal_newlines=True,
                listener=line_handler)
        assert rc == 0
        assert output == ['hello\n', 'boo']

    def test_streamed_call_with_stdin_fails(self):
        exefile = self.wd.write(PROGRAM_NAME, create_program(exit_code=0))
        command = ['python', exefile]
        sc = SystemContext()
        with pytest.raises(ValueError):
            sc.streamed_call(command, universal_newlines=True,
                    stdin=subprocess.PIPE)

    def test_streamed_call_with_stdout_fails(self):
        exefile = self.wd.write(PROGRAM_NAME, create_program(exit_code=0))
        command = ['python', exefile]
        sc = SystemContext()
        with pytest.raises(ValueError):
            sc.streamed_call(command, universal_newlines=True,
                    stdout=subprocess.PIPE)
