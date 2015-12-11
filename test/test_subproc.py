#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
test_subproc
----------------------------------

Tests for `subproc` module.
"""
import subprocess
from ttt.subproc import call_output

class TestSubprocess:
    def test_call(self):
        output = call_output('for i in {5..1}; do echo blah blah blah $i; sleep 1; done', shell=True, universal_newlines=True)
        assert output == 'blah blah blah 5\nblah blah blah 4\nblah blah blah 3\nblah blah blah 2\nblah blah blah 1\n'

    def test_call_raise(self):
        cmd = 'for i in {5..1}; do echo blah blah blah $i; sleep 1; done; false'
        try:
            call_output(cmd, shell=True, universal_newlines=True)
        except subprocess.CalledProcessError as e:
            assert e.returncode == 1
            assert e.cmd == cmd
            assert e.output == 'blah blah blah 5\nblah blah blah 4\nblah blah blah 3\nblah blah blah 2\nblah blah blah 1\n'
