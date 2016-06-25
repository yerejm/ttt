#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
test_systemcontext
----------------------------------

Tests for `systemcontext` module.
"""
import os
import subprocess

import pytest
from testfixtures import TempDirectory

from ttt.systemcontext import SystemContext

PROGRAM_NAME = 'test.py'
def create_program(exit_code=0):
    program = [ 'import sys', 'print("hello")' ]
    program.append('sys.exit({})'.format(exit_code))
    return os.linesep.join(program).encode('utf-8')

def create_stdout_stderr_program(exit_code=0):
    program = [
            'import sys',
            'import os',
            'sys.stdout.write("hello stdout" + os.linesep)',
            'sys.stderr.write("hello stderr" + os.linesep)',
            ]
    program.append('sys.exit({})'.format(exit_code))
    return os.linesep.join(program).encode('utf-8')

def python_command(exefile):
    # tox runs a deprecated site.py; ignore them or else tests watching stderr
    # will flag false positives
    return ['python', '-W', 'ignore::DeprecationWarning', exefile]

class TestSystemContext:
    def setup(self):
        self.wd = wd = TempDirectory()
        wd.write('test1.txt', b'')
        wd.write('dummy2.txt', b'')
        wd.makedir('test');
        wd.write(['test', 'test3.txt'], b'')

    def teardown(self):
        TempDirectory.cleanup_all()

    def test_execute(self):
        sc = SystemContext()

        exefile = self.wd.write(PROGRAM_NAME, create_program(exit_code=0))
        output = sc.execute(python_command(exefile), universal_newlines=True)
        assert output == [ 'hello' ]

    def test_execute_error(self):
        sc = SystemContext()

        exefile = self.wd.write(PROGRAM_NAME, create_program(exit_code=1))
        with pytest.raises(subprocess.CalledProcessError):
            sc.execute(python_command(exefile), universal_newlines=True)

    def test_checked_call(self):
        sc = SystemContext()

        exefile = self.wd.write(PROGRAM_NAME, create_program(exit_code=0))
        assert 0 == sc.checked_call(python_command(exefile), universal_newlines=True)

    def test_checked_call_error(self):
        sc = SystemContext()

        exefile = self.wd.write(PROGRAM_NAME, create_program(exit_code=1))
        with pytest.raises(subprocess.CalledProcessError):
            sc.checked_call(python_command(exefile), universal_newlines=True)

    def test_streamed_call(self):
        sc = SystemContext()

        exefile = self.wd.write(PROGRAM_NAME, create_program(exit_code=0))
        assert sc.streamed_call(python_command(exefile), universal_newlines=True) == (0, ['hello'], [])

    def test_streamed_call_with_stdout_stderr(self):
        sc = SystemContext()

        exefile = self.wd.write(PROGRAM_NAME, create_stdout_stderr_program(exit_code=0))
        rc, out, err = sc.streamed_call(python_command(exefile), universal_newlines=True)
        assert rc == 0
        assert 'hello stderr' in out
        assert 'hello stdout' in out
        # Why can't this be an assertion against an array? On linux and mac,
        # the order of the output is in the opposite order that the program
        # prints. Curiously, the expected order is correct in windows.
        assert err == []

    def test_streamed_call_error(self):
        sc = SystemContext()

        exefile = self.wd.write(PROGRAM_NAME, create_program(exit_code=1))
        assert sc.streamed_call(python_command(exefile), universal_newlines=True) == (1, ['hello'], [])

    def test_streamed_call_with_handler(self):
        output = []
        def line_handler(channel, line):
            output.append(line)
            output.append('boo')

        exefile = self.wd.write(PROGRAM_NAME, create_program(exit_code=0))
        sc = SystemContext()
        assert sc.streamed_call(python_command(exefile), universal_newlines=True,
                listener=line_handler) == (0, ['hello'], [])
        assert output == ['hello', 'boo']

    def test_streamed_call_with_stdin_fails(self):
        exefile = self.wd.write(PROGRAM_NAME, create_program(exit_code=0))
        sc = SystemContext()
        with pytest.raises(ValueError):
            sc.streamed_call(python_command(exefile), universal_newlines=True,
                    stdin=subprocess.PIPE)

    def test_streamed_call_with_stdout_fails(self):
        exefile = self.wd.write(PROGRAM_NAME, create_program(exit_code=0))
        sc = SystemContext()
        with pytest.raises(ValueError):
            sc.streamed_call(python_command(exefile), universal_newlines=True,
                    stdout=subprocess.PIPE)
