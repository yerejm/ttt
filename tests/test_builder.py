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


LOG_IDX_GENERATE = 2
LOG_IDX_BUILD = 3


class TestBuilder:
    def setup_method(self):
        cmake_source_directory = TempDirectory()
        self.cmake_source_path = cmake_source_directory.path
        cmake_build_directory = TempDirectory()
        self.cmake_build_path = cmake_build_directory.path
        cmake_source_directory.write("CMakeLists.txt", b"project(test)")

    def teardown_method(self):
        TempDirectory.cleanup_all()

    def test_build_with_generator(self):
        builder = create_builder(
            self.cmake_source_path, self.cmake_build_path, generator="Ninja"
        )
        builder()

        assert exists(join(self.cmake_build_path, "CMakeFiles"))
        assert exists(join(self.cmake_build_path, "build.ninja"))

    def test_build_with_default_build_type(self):
        log = []
        builder = create_builder(
            self.cmake_source_path, self.cmake_build_path, command_log=log
        )
        builder()

        assert "-DCMAKE_BUILD_TYPE=Debug" in log[LOG_IDX_GENERATE][0]
        assert ["--config", "Debug"] == log[LOG_IDX_BUILD][0][-2:]

    def test_build_with_build_type(self):
        log = []
        builder = create_builder(
            self.cmake_source_path,
            self.cmake_build_path,
            build_config="Release",
            command_log=log,
        )
        builder()

        assert "-DCMAKE_BUILD_TYPE=Release" in log[LOG_IDX_GENERATE][0]
        assert ["--config", "Release"] == log[LOG_IDX_BUILD][0][-2:]

    def test_build_with_none_define(self):
        log = []
        builder = create_builder(
            self.cmake_source_path,
            self.cmake_build_path,
            defines=None,
            command_log=log,
        )
        builder()

        assert ["-DCMAKE_BUILD_TYPE=Debug"] == [
            arg for arg in log[LOG_IDX_GENERATE][0] if "-D" in arg
        ]

    def test_build_with_define(self):
        log = []
        builder = create_builder(
            self.cmake_source_path,
            self.cmake_build_path,
            defines=["FOO=BAR", "A:STRING=VALUE"],
            command_log=log,
        )
        builder()

        assert "-DFOO=BAR" in log[LOG_IDX_GENERATE][0]
        assert "-DA:STRING=VALUE" in log[LOG_IDX_GENERATE][0]

    def test_build_with_conanfile_txt(self):
        conanfile = os.path.join(self.cmake_source_path, "conanfile.txt")
        with open(conanfile, "wb") as file:
            file.write(b"[layout]\ncmake_layout")
        log = []
        builder = create_builder(
            self.cmake_source_path,
            self.cmake_build_path,
            defines=None,
            command_log=log,
        )
        builder()

        conan_cmake = os.path.join(self.cmake_build_path, "conan_provider.cmake")
        assert os.path.exists(conan_cmake)
        assert f"-DCMAKE_PROJECT_TOP_LEVEL_INCLUDES={conan_cmake}" in [
            arg for arg in log[LOG_IDX_GENERATE][0] if "-D" in arg
        ]

    def test_build_with_conanfile_py(self):
        conanfile = os.path.join(self.cmake_source_path, "conanfile.py")
        with open(conanfile, "wb") as file:
            file.write(b"[layout]\ncmake_layout")
        log = []
        builder = create_builder(
            self.cmake_source_path,
            self.cmake_build_path,
            defines=None,
            command_log=log,
        )
        builder()

        conan_cmake = os.path.join(self.cmake_build_path, "conan_provider.cmake")
        assert os.path.exists(conan_cmake)
        print(log)
        assert f"-DCMAKE_PROJECT_TOP_LEVEL_INCLUDES={conan_cmake}" in [
            arg for arg in log[LOG_IDX_GENERATE][0] if "-D" in arg
        ]

    def test_good_build(self):
        build_file = "test.sln" if platform.system() == "Windows" else "Makefile"
        builder = create_builder(self.cmake_source_path, self.cmake_build_path)
        builder()

        assert exists(join(self.cmake_build_path, "CMakeFiles"))
        assert exists(join(self.cmake_build_path, build_file))

        conan_cmake = os.path.join(self.cmake_build_path, "conan_provider.cmake")
        assert not os.path.exists(conan_cmake)

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
        )

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
        )

        cmake_source_directory.write("CMakeLists.txt", b"project(test)")
        builder()
        assert exists(join(build_path, "CMakeFiles"))
