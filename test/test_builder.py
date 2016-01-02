#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
test_builder
----------------------------------

Tests for `builder` module.
"""

import os
import platform

from testfixtures import TempDirectory

from ttt.builder import create_builder
from ttt.builder import CMakeError
from ttt.builder import CMakeInvalidAbsolutePathError
from ttt.systemcontext import SystemContext

class CommandCaptureContext:
    def __init__(self):
        self.calls = []
    def checked_call(self, *args, **kwargs):
        self.calls.append(args)

class TestCMake:

    def test_default_build(self):
        ccc = CommandCaptureContext()
        builder = create_builder(ccc, '/path/to/source', '/path/to/build')
        builder.build()

        assert ccc.calls == [
                (['cmake', '-H/path/to/source', '-B/path/to/build'],),
                (['cmake', '--build', '/path/to/build'],),
                ]

    def test_build_with_generator(self):
        ccc = CommandCaptureContext()
        builder = create_builder(ccc, '/path/to/source', '/path/to/build', 'Ninja')
        builder.build()

        assert ccc.calls == [
                (['cmake', '-G', 'Ninja', '-H/path/to/source', '-B/path/to/build'],),
                (['cmake', '--build', '/path/to/build'],),
                ]

class TestCMakeSlow:
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
        builder = create_builder(SystemContext(), self.cmake_source_path, self.cmake_build_path)
        builder.build()

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

        builder = create_builder(SystemContext(), source_path, build_path)
        try:
            builder.build()
        except CMakeError as e:
            assert e.command == expected

    def test_bad_build_from_relative_path(self):
        error = None
        try:
            create_builder(SystemContext(), 'dummy', self.cmake_build_path)
        except CMakeInvalidAbsolutePathError as e:
            error = e
        assert str(error) == 'Watch path dummy must be absolute'

        error = None
        try:
            create_builder(SystemContext(), self.cmake_source_path, 'dummy')
        except CMakeInvalidAbsolutePathError as e:
            error = e
        assert str(error) == 'Build path dummy must be absolute'

