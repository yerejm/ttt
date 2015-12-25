#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
test_cmake
----------------------------------

Tests for `cmake` module.
"""

import os
import pytest
import platform
import subprocess
from testfixtures import TempDirectory

from ttt.cmake import CMakeContext, CMakeError
from ttt.systemcontext import SystemContext

DEFAULT_BUILD_WINDOWS = 'Visual Studio 14 2015'
DEFAULT_BUILD_UNIX = 'Unix Makefiles'

def default_build_system():
    default = DEFAULT_BUILD_UNIX
    if platform.system() == 'Windows':
        default = DEFAULT_BUILD_WINDOWS
    return default

def command_missing(command):
    locator = 'where' if platform.system() == 'Windows' else 'which'
    try:
        subprocess.check_call([locator, command])
        return False
    except:
        return True

class TestCreateBuildArea:
    def setup(self):
        work_directory = TempDirectory()
        work_directory.write(('source', 'CMakeLists.txt'), b'project(test)')
        self.old_cwd = os.getcwd()
        os.chdir(work_directory.path)

    def teardown(self):
        os.chdir(self.old_cwd)
        TempDirectory.cleanup_all()

    def test_cmake_invalid_source_error(self):
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
            assert str(e) == str(expected)

class TestDefaultBuildArea:

    def teardown(self):
        TempDirectory.cleanup_all()

    def test_default_build(self):
        build_file = 'test.sln' if platform.system() == 'Windows' else 'Makefile'
        cmake_source_directory = TempDirectory()
        cmake_source_path = cmake_source_directory.path
        cmake_build_directory = TempDirectory()
        cmake_build_path = cmake_build_directory.path
        cmake_source_directory.write('CMakeLists.txt', b'project(test)')

        ctx = CMakeContext(SystemContext())
        ctx.build(cmake_source_path, cmake_build_path)

        assert os.path.exists(os.path.join(cmake_build_path, 'CMakeFiles'))
        assert os.path.exists(os.path.join(cmake_build_path, build_file))

@pytest.mark.skipif(command_missing('ninja'), reason="ninja not installed")
class TestNinjaBuildArea:

    def teardown(self):
        TempDirectory.cleanup_all()

    def test_ninja_build(self):
        cmake_source_directory = TempDirectory()
        cmake_source_path = cmake_source_directory.path
        cmake_build_directory = TempDirectory()
        cmake_build_path = cmake_build_directory.path
        cmake_source_directory.write('CMakeLists.txt', b'project(test)')

        ctx = CMakeContext(SystemContext(), 'Ninja')
        ctx.build(cmake_source_path, cmake_build_path)

        assert os.path.exists(os.path.join(cmake_build_path, 'CMakeFiles'))
        assert os.path.exists(os.path.join(cmake_build_path, 'build.ninja'))

@pytest.mark.skipif(command_missing('make'), reason="make not installed")
class TestMakeBuildArea:

    def teardown(self):
        TempDirectory.cleanup_all()

    def test_make_build(self):
        cmake_source_directory = TempDirectory()
        cmake_source_path = cmake_source_directory.path
        cmake_build_directory = TempDirectory()
        cmake_build_path = cmake_build_directory.path
        cmake_source_directory.write('CMakeLists.txt', b'project(test)')

        ctx = CMakeContext(SystemContext(), 'Unix Makefiles')
        ctx.build(cmake_source_path, cmake_build_path)

        assert os.path.exists(os.path.join(cmake_build_path, 'CMakeFiles'))
        assert os.path.exists(os.path.join(cmake_build_path, 'Makefile'))

class TestInvalidBuildArea:

    def teardown(self):
        TempDirectory.cleanup_all()

    def test_bad_build(self):
        cmake_source_directory = TempDirectory()
        cmake_source_path = cmake_source_directory.path
        cmake_build_directory = TempDirectory()
        cmake_build_path = cmake_build_directory.path
        cmake_source_directory.write('CMakeLists.txt', b'project(test)')

        ctx = CMakeContext(SystemContext(), 'dummy')
        with pytest.raises(CMakeError):
            ctx.build(cmake_source_path, cmake_build_path)
        assert not os.path.exists(os.path.join(cmake_build_path, 'CMakeFiles'))

