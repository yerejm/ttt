#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
test_subproc
----------------------------------

Tests for `subproc` module.
"""
import subprocess
import os
import io
import sys
import re
from testfixtures import TempDirectory

from ttt.subproc import call_output

from contextlib import contextmanager

PROGRAM_NAME = 'test.py'

@contextmanager
def stdout_redirector(stream):
    old_stdout = sys.stdout
    sys.stdout = stream
    try:
        yield
    finally:
        sys.stdout = old_stdout

def create_program(exit_code=None):
    program = [
        'import time',
        'import sys',
        'for x in range(1, 3):',
        '    print("blah blah blah " + str(x))',
        '    time.sleep(1)'
    ]
    if exit_code is None:
        raise "Exit code must be given"
    program.append('sys.exit({})'.format(exit_code))
    return os.linesep.join(program).encode('utf-8')

class TestSubprocess:
    def setup(self):
        self.tmp = TempDirectory()
        self.command = ['python', os.path.join(self.tmp.path, PROGRAM_NAME)]

    def teardown(self):
        TempDirectory.cleanup_all()

    def test_call(self):
        self.tmp.write(PROGRAM_NAME, create_program(exit_code=0))
        rc = call_output(self.command, universal_newlines=True)
        assert rc == 0

    def test_call_raise(self):
        self.tmp.write(PROGRAM_NAME, create_program(exit_code=1))
        rc = call_output(self.command, universal_newlines=True)
        assert rc != 0

    def test_call_with_handler(self):
        output = []
        def line_handler(line):
            output.append(line)
            output.append('boo')

        self.tmp.write(PROGRAM_NAME, create_program(exit_code=0))
        rc = call_output(self.command, universal_newlines=True,
                listener=line_handler)
        assert rc == 0
        assert output == ['blah blah blah 1\n', 'boo', 'blah blah blah 2\n', 'boo']
