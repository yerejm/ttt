"""
ttt.builder
~~~~~~~~~~~~
This module implements the cmake builder.
:copyright: (c) yerejm
"""

import os
import errno
import shutil
import subprocess
from functools import partial


def create_builder(watch_path, build_path,
                   generator=None, build_type=None):
    """Constructs a partially evaluated function object.

    This function object represents the execution of the `cmake` command on
    a source tree to either create a new build area or to rebuild an existing
    build area.

    :param watch_path: the absolute root directory path of the source tree
        where the CMakeLists.txt file exists
    :param build_path: the absolute root directory path where build objects and
        binaries are output during compilation
    :param build_type: indicates the type of build, e.g. release, debug
    :param generator: (optional) the cmake generator. Values are the same as
        provided by the cmake usage output. e.g. "Unix Makefile", "Ninja"
        This is because it is passed through via the -G option. Not providing
        it is the same as not providing it to the cmake command and will make
        cmake use the default generator for the executing platform
    """
    if not os.path.isabs(watch_path):
        raise IOError(
            errno.EINVAL, "Watch path {} must be absolute".format(watch_path)
        )
    if not os.path.isabs(build_path):
        raise IOError(
            errno.EINVAL, "Build path {} must be absolute".format(build_path)
        )
    return partial(
        execute,
        [
            partial(cmake_generate, watch_path, build_path,
                    build_type, generator),
            partial(cmake_build, build_path, build_type)
        ]
    )


def execute(commands):
    """Executes the list of callable objects.

    Each callable object is a command generator that when called returns a
    command that can be executed as a subprocess. The command returned will be
    a list for subprocess's non-string form (ie ['ls', '-la'], not 'ls -la')
    to avoid shell escaping mishaps.

    :param commands: a list of callable objects
    """
    from ttt.subproc import checked_call
    for command_generator in commands:
        command = command_generator()
        if command:  # Note that command may be None (or empty list)
            checked_call(command, stderr=subprocess.STDOUT)


def cmake_generate(watch_path, build_path, build_type, generator):
    """Generates the command for cmake that will create a build area for a
    source tree.

    If the build area has already been created, then the command is None.

    If the build area has already been created, but the cmake command that
    generated it no longer exists, then the build area is removed first before
    the command is generated.

    :param watch_path: the absolute root directory path of the source tree
        where the CMakeLists.txt file exists
    :param build_path: the absolute root directory path where build objects and
        binaries are output during compilation
    :param build_type: indicates the type of build, e.g. release, debug
    :param generator: (optional) the cmake generator. Values are the same as
        provided by the cmake usage output. e.g. "Unix Makefile", "Ninja"
        This is because it is passed through via the -G option. Not providing
        it is the same as not providing it to the cmake command and will make
        cmake use the default generator for the executing platform
    :return: command to execute as a subprocess in list form
    """
    cmake_cache_file = os.path.join(build_path, 'CMakeCache.txt')
    if os.path.exists(cmake_cache_file):
        # If the cmake version has changed since the build area was created,
        # recreate it.
        with open(cmake_cache_file, 'r') as f:
            for line in f:
                if 'CMAKE_COMMAND:INTERNAL' in line:
                    _, cmake_path = line.rstrip().split('=')
                    if not os.path.exists(cmake_path):
                        shutil.rmtree(build_path)
                    break

    if not os.path.exists(os.path.join(build_path, 'CMakeFiles')):
        command = ['cmake']
        if generator is not None:
            command.append('-G')
            command.append(generator)
        command.append('-H{}'.format(watch_path))
        command.append('-B{}'.format(build_path))
        # this does nothing for the MSVC generator
        if build_type is not None:
            command.append('-DCMAKE_BUILD_TYPE={}'.format(build_type))
        return command


def cmake_build(build_path, build_type):
    """Generates the cmake command to (re)build the build area.

    :param build_path: the absolute root directory path where build objects and
        binaries are output during compilation
    :param build_type: indicates the type of build, e.g. release, debug
    :return: command to execute as a subprocess in list form
    """
    command = [
        'cmake',
        # the order is important. --build must come first
        '--build', build_path,
    ]
    if build_type is not None:
        # necessary for multi-configuration build systems, e.g. MSVC
        # should be harmless otherwise
        command.append('--config')
        command.append(build_type)
    return command
