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

@contextmanager
def stdout_redirector(stream):
    old_stdout = sys.stdout
    sys.stdout = stream
    try:
        yield
    finally:
        sys.stdout = old_stdout

class MockContext:
    def streamed_call(self, command, listener):
        pass
    def glob_files(self, path, selector):
        return []

class TestExecutor:
    def test_test_success_creates_empty_filter(self):
        buildpath = '/path/to/build'
        testdict = {}
        sc = MockContext()
        e = Executor(sc)
        e.test(buildpath, testdict)

    def test_test_failure_creates_filter(self):
        buildpath = '/path/to/build'
        testdict = {}
        sc = MockContext()
        e = Executor(sc)
        e.test(buildpath, testdict)

    def test_test_failure_runs_only_failure(self):
        buildpath = '/path/to/build'
        testdict = {}
        sc = MockContext()
        e = Executor(sc)
        e.test(buildpath, testdict)

    def test_test_failure_then_success_reruns_all(self):
        buildpath = '/path/to/build'
        testdict = {}
        sc = MockContext()
        e = Executor(sc)
        e.test(buildpath, testdict)

    def test_discovers_added_tests(self):
        buildpath = '/path/to/build'
        testdict = {}
        sc = MockContext()
        e = Executor(sc)
        e.test(buildpath, testdict)

    def test_discovers_deleted_tests(self):
        buildpath = '/path/to/build'
        testdict = {}
        sc = MockContext()
        e = Executor(sc)
        e.test(buildpath, testdict)

