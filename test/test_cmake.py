#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
test_cmake
----------------------------------

Tests for `cmake` module.
"""

import os
import platform
import re
import pytest
from testfixtures import TempDirectory

from ttt.cmake import CMakeContext, CMakeError, InvalidCMakeGenerator

def is_windows():
    return platform.system() == 'Windows'

class TestCreateBuildArea:
    def setup(self):
        work_directory = TempDirectory()
        work_directory.write(('source', 'CMakeLists.txt'), b'project(test)')
        self.old_cwd = os.getcwd()
        os.chdir(work_directory.path)

    def teardown(self):
        os.chdir(self.old_cwd)
        TempDirectory.cleanup_all()

    def test_build_file_requires_build(self):
        ctx = CMakeContext('source')
        assert ctx.build_file() is None
        ctx.build()
        assert ctx.build_file() is not None

    def test_cmake_error(self):
        source_path = '{}'.format(os.path.join(os.getcwd(), 'dummy'))
        expected = [
            'cmake',
            '-G', 'Unix Makefiles',
            '-H{}'.format(source_path),
            '-B{}'.format(os.path.join(os.getcwd(), 'dummy-build'))
        ]

        ctx = CMakeContext('dummy')
        try:
            ctx.build()
        except CMakeError as e:
            assert e.command == expected
            assert str(e) == str(expected)

    def test_create_build_area_in_cwd(self):
        ctx = CMakeContext('source')
        ctx.build()

        assert os.path.exists(os.path.join(os.getcwd(), 'source'))
        assert os.path.exists(os.path.join(os.getcwd(), 'source-build', 'CMakeFiles'))

    def test_create_existing_build_area(self):
        ctx = CMakeContext('source')
        ctx.build()
        create_time = os.path.getctime(os.path.join(os.getcwd(), 'source-build', 'CMakeFiles'))
        ctx.build()
        recreate_time = os.path.getctime(os.path.join(os.getcwd(), 'source-build', 'CMakeFiles'))

        assert create_time == recreate_time

class TestDefaultBuildArea:

    def teardown(self):
        TempDirectory.cleanup_all()

    def test_default_build(self):
        cmake_source_directory = TempDirectory()
        cmake_source_path = cmake_source_directory.path
        cmake_build_directory = TempDirectory()
        cmake_build_path = cmake_build_directory.path
        cmake_source_directory.write('CMakeLists.txt', b'project(test)')

        ctx = CMakeContext(cmake_source_path, cmake_build_path)
        ctx.build()

        default_build_command = 'msbuild' if is_windows() else 'make'
        default_build_file_pattern = 'test.sln' if is_windows() else 'Makefile'

        assert ctx.build_command() == default_build_command
        assert ctx.build_file() == default_build_file_pattern
        assert os.path.exists(os.path.join(ctx.build_path, 'CMakeFiles'))
        assert os.path.exists(os.path.join(ctx.build_path, 'Makefile'))
        assert ctx.watch_path == cmake_source_path
        assert ctx.build_path == cmake_build_path

class TestNinjaBuildArea:

    def teardown(self):
        TempDirectory.cleanup_all()

    def test_ninja_build(self):
        cmake_source_directory = TempDirectory()
        cmake_source_path = cmake_source_directory.path
        cmake_build_directory = TempDirectory()
        cmake_build_path = cmake_build_directory.path
        cmake_source_directory.write('CMakeLists.txt', b'project(test)')

        ctx = CMakeContext(cmake_source_path, cmake_build_path, 'Ninja')
        ctx.build()

        assert ctx.build_command() == 'ninja'
        assert ctx.build_file() == 'build.ninja'
        assert os.path.exists(os.path.join(ctx.build_path, 'CMakeFiles'))
        assert os.path.exists(os.path.join(ctx.build_path, 'build.ninja'))
        assert ctx.watch_path == cmake_source_path
        assert ctx.build_path == cmake_build_path

class TestMakeBuildArea:

    def teardown(self):
        TempDirectory.cleanup_all()

    def test_make_build(self):
        cmake_source_directory = TempDirectory()
        cmake_source_path = cmake_source_directory.path
        cmake_build_directory = TempDirectory()
        cmake_build_path = cmake_build_directory.path
        cmake_source_directory.write('CMakeLists.txt', b'project(test)')

        ctx = CMakeContext(cmake_source_path, cmake_build_path, 'Unix Makefiles')
        ctx.build()

        assert ctx.build_command() == 'make'
        assert ctx.build_file() == 'Makefile'
        assert os.path.exists(os.path.join(ctx.build_path, 'CMakeFiles'))
        assert os.path.exists(os.path.join(ctx.build_path, 'Makefile'))
        assert ctx.watch_path == cmake_source_path
        assert ctx.build_path == cmake_build_path

class TestInvalidBuildArea:

    def teardown(self):
        TempDirectory.cleanup_all()

    def test_bad_build(self):
        cmake_source_directory = TempDirectory()
        cmake_source_path = cmake_source_directory.path
        cmake_build_directory = TempDirectory()
        cmake_build_path = cmake_build_directory.path
        cmake_source_directory.write('CMakeLists.txt', b'project(test)')

        with pytest.raises(InvalidCMakeGenerator):
            CMakeContext(cmake_source_path, cmake_build_path, 'dummy')
        assert not os.path.exists(os.path.join(cmake_build_path, 'CMakeFiles'))

