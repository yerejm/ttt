#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
test_builder
----------------------------------

Tests for `builder` module.
"""

import os
from os.path import exists, join
import platform

from testfixtures import TempDirectory

from ttt.builder import create_builder


def find_in_file(filename, string):
    with open(filename, "r") as f:
        for line in f:
            if string in line:
                return line
    return False


class TestCMake:
    def setup_method(self):
        cmake_source_directory = TempDirectory()
        self.cmake_source_path = cmake_source_directory.path
        cmake_build_directory = TempDirectory()
        self.cmake_build_path = cmake_build_directory.path
        cmake_source_directory.write("CMakeLists.txt", b"project(test)")

    def teardown_method(self):
        TempDirectory.cleanup_all()

    def test_build_with_generator(self):
        builder = create_builder(self.cmake_source_path, self.cmake_build_path, "Ninja")
        builder()

        assert exists(join(self.cmake_build_path, "CMakeFiles"))
        assert exists(join(self.cmake_build_path, "build.ninja"))

    def test_build_with_default_build_type(self):
        builder = create_builder(self.cmake_source_path, self.cmake_build_path)
        builder()

        cmakecache = join(self.cmake_build_path, "CMakeCache.txt")
        assert exists(cmakecache)
        assert not find_in_file(cmakecache, "CMAKE_BUILD_TYPE:UNINITIALIZED=")

    def test_build_with_build_type(self):
        builder = create_builder(
            self.cmake_source_path, self.cmake_build_path, build_type="release"
        )
        builder()

        cmakecache = join(self.cmake_build_path, "CMakeCache.txt")
        assert exists(cmakecache)
        assert find_in_file(cmakecache, "CMAKE_BUILD_TYPE:UNINITIALIZED=release")

    def test_build_with_none_define(self):
        builder = create_builder(
            self.cmake_source_path,
            self.cmake_build_path,
            build_type="release",
            defines=None,
        )
        builder()

        cmakecache = join(self.cmake_build_path, "CMakeCache.txt")
        assert exists(cmakecache)

    def test_build_with_define(self):
        builder = create_builder(
            self.cmake_source_path,
            self.cmake_build_path,
            build_type="release",
            defines=["FOO=BAR", "A:STRING=VALUE"],
        )
        builder()

        cmakecache = join(self.cmake_build_path, "CMakeCache.txt")
        assert exists(cmakecache)
        assert find_in_file(cmakecache, "FOO:UNINITIALIZED=BAR")
        assert find_in_file(cmakecache, "A:STRING=VALUE")

    def test_good_build(self):
        build_file = (
            "test.sln" if platform.system() == "Windows" else "Makefile"
        )  # noqa
        builder = create_builder(self.cmake_source_path, self.cmake_build_path)
        builder()

        assert exists(join(self.cmake_build_path, "CMakeFiles"))
        assert exists(join(self.cmake_build_path, build_file))

    def test_no_cmakelists_txt(self):
        source_path = "{}".format(join(os.getcwd(), "dummy"))
        build_path = join(os.getcwd(), "dummy-build")

        builder = create_builder(source_path, build_path)
        raised = None
        try:
            builder()
        except IOError as e:
            raised = str(e)
        assert raised == "[Errno 22] No CMakeLists.txt detected in {}".format(
            source_path
        )  # noqa

    def test_bad_build_from_relative_path(self):
        error = None
        try:
            create_builder("dummy", self.cmake_build_path)
        except IOError as e:
            error = e
        assert "Watch path dummy must be absolute" in str(error)

        error = None
        try:
            create_builder(self.cmake_source_path, "dummy")
        except IOError as e:
            error = e
        assert "Build path dummy must be absolute" in str(error)

    def test_clean_build(self):
        cmake_source_directory = TempDirectory()
        source_path = cmake_source_directory.path
        cmake_build_directory = TempDirectory()
        build_path = cmake_build_directory.path

        builder = create_builder(source_path, build_path)
        raised = None
        try:
            builder()
        except IOError as e:
            raised = str(e)
        assert raised == "[Errno 22] No CMakeLists.txt detected in {}".format(
            source_path
        )  # noqa

        cmake_source_directory.write("CMakeLists.txt", b"project(test)")
        builder()
        assert exists(join(build_path, "CMakeFiles"))
