#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
test_builder
----------------------------------

Tests for `builder` module.
"""

import os
import platform
import subprocess

from testfixtures import TempDirectory
from ttt.builder import create_builder


def find_in_file(filename, string):
    with open(filename, 'r') as f:
        for line in f:
            if string in line:
                return line
    return False


class TestCMake:
    def setup(self):
        cmake_source_directory = TempDirectory()
        self.cmake_source_path = cmake_source_directory.path
        cmake_build_directory = TempDirectory()
        self.cmake_build_path = cmake_build_directory.path
        cmake_source_directory.write('CMakeLists.txt', b'project(test)')

    def teardown(self):
        TempDirectory.cleanup_all()

    def test_build_with_generator(self):
        builder = create_builder(self.cmake_source_path, self.cmake_build_path, 'Ninja')
        builder()

        assert os.path.exists(os.path.join(self.cmake_build_path, 'CMakeFiles'))
        assert os.path.exists(os.path.join(self.cmake_build_path, 'build.ninja'))

    def test_build_with_default_build_type(self):
        builder = create_builder(self.cmake_source_path, self.cmake_build_path)
        builder()

        cmakecache = os.path.join(self.cmake_build_path, 'CMakeCache.txt')
        assert os.path.exists(cmakecache)
        assert find_in_file(cmakecache, 'CMAKE_BUILD_TYPE:STRING=' + os.linesep)

    def test_build_with_build_type(self):
        builder = create_builder(self.cmake_source_path, self.cmake_build_path,
                                 build_type="release")
        builder()

        cmakecache = os.path.join(self.cmake_build_path, 'CMakeCache.txt')
        assert os.path.exists(cmakecache)
        assert find_in_file(cmakecache, 'CMAKE_BUILD_TYPE:STRING=release' + os.linesep)

    def test_build_with_none_define(self):
        builder = create_builder(self.cmake_source_path, self.cmake_build_path,
                                 build_type="release",
                                 defines=None)
        builder()

        cmakecache = os.path.join(self.cmake_build_path, 'CMakeCache.txt')
        assert os.path.exists(cmakecache)

    def test_build_with_define(self):
        builder = create_builder(self.cmake_source_path, self.cmake_build_path,
                                 build_type="release",
                                 defines=['FOO=BAR', 'A:STRING=VALUE'])
        builder()

        cmakecache = os.path.join(self.cmake_build_path, 'CMakeCache.txt')
        assert os.path.exists(cmakecache)
        assert find_in_file(cmakecache, 'FOO:UNINITIALIZED=BAR' + os.linesep)
        assert find_in_file(cmakecache, 'A:STRING=VALUE' + os.linesep)

    def test_good_build(self):
        build_file = 'test.sln' if platform.system() == 'Windows' else 'Makefile'
        builder = create_builder(self.cmake_source_path, self.cmake_build_path)
        builder()

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

        builder = create_builder(source_path, build_path)
        try:
            builder()
        except subprocess.CalledProcessError as e:
            assert e.cmd == expected

    def test_bad_build_from_relative_path(self):
        error = None
        try:
            create_builder('dummy', self.cmake_build_path)
        except IOError as e:
            error = e
        assert 'Watch path dummy must be absolute' in str(error)

        error = None
        try:
            create_builder(self.cmake_source_path, 'dummy')
        except IOError as e:
            error = e
        assert 'Build path dummy must be absolute' in str(error)

