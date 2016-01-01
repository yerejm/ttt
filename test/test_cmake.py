#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
test_cmake
----------------------------------

Tests for `cmake` module.
"""

import os
import platform

import pytest
from testfixtures import TempDirectory

from ttt.cmake import CMakeContext, CMakeError
from ttt.systemcontext import SystemContext

class CommandCaptureContext:
    def __init__(self):
        self.calls = []
    def checked_call(self, *args, **kwargs):
        self.calls.append(args)

class TestCMakeContext:

    def test_default_build(self):
        ccc = CommandCaptureContext()
        ctx = CMakeContext(ccc)
        ctx.build('/path/to/source', '/path/to/build')

        assert ccc.calls == [
                (['cmake', '-H/path/to/source', '-B/path/to/build'],),
                (['cmake', '--build', '/path/to/build'],),
                ]

    def test_build_with_generator(self):
        ccc = CommandCaptureContext()
        ctx = CMakeContext(ccc, 'Ninja')
        ctx.build('/path/to/source', '/path/to/build')

        assert ccc.calls == [
                (['cmake', '-G', 'Ninja', '-H/path/to/source', '-B/path/to/build'],),
                (['cmake', '--build', '/path/to/build'],),
                ]

class TestCMakeContextSlow:
    def setup(self):
        cmake_source_directory = TempDirectory()
        self.cmake_source_path = cmake_source_directory.path
        cmake_build_directory = TempDirectory()
        self.cmake_build_path = cmake_build_directory.path
        cmake_source_directory.write('CMakeLists.txt', b'project(test)')

    def teardown(self):
        TempDirectory.cleanup_all()

    def test_good_build(self):
        build_file = 'test.sln' if platform.system() == 'Windows' else 'Makefile'
        ctx = CMakeContext(SystemContext())
        ctx.build(self.cmake_source_path, self.cmake_build_path)

        assert os.path.exists(os.path.join(self.cmake_build_path, 'CMakeFiles'))
        assert os.path.exists(os.path.join(self.cmake_build_path, build_file))

    def test_bad_build(self):
        source_path = '{}'.format(os.path.join(os.getcwd(), 'dummy'))
        build_path = os.path.join(os.getcwd(), 'dummy-build')
        expected = [
            'cmake',
            '-H{}'.format(source_path),
            '-B{}'.format(build_path)
        ]

        ctx = CMakeContext(SystemContext())
        try:
            ctx.build(source_path, build_path)
        except CMakeError as e:
            assert e.command == expected

    def test_bad_build_from_relative_path(self):
        ctx = CMakeContext(SystemContext())
        with pytest.raises(Exception):
            ctx.build('dummy', self.cmake_build_path)
        with pytest.raises(Exception):
            ctx.build(self.cmake_source_path, 'dummy')

