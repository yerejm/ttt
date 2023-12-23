"""
ttt.builder
~~~~~~~~~~~~
This module implements the cmake builder.
:copyright: (c) yerejm
"""

import errno
from functools import partial
import glob
import os
import platform
import shutil
import subprocess


def create_builder(watch_path, build_path, **kwargs):
    """Constructs a partially evaluated function object.

    This function object represents the execution of the `cmake` command on
    a source tree to either create a new build area or to rebuild an existing
    build area.

    :param watch_path: the absolute root directory path of the source tree
        where the CMakeLists.txt file exists
    :param build_path: the absolute root directory path where build objects and
        binaries are output during compilation
    :param generator: (optional) the cmake generator. Values are the same as
        provided by the cmake usage output. e.g. "Unix Makefile", "Ninja"
        This is because it is passed through via the -G option. Not providing
        it is the same as not providing it to the cmake command and will make
        cmake use the default generator for the executing platform
    :param build_config: (optional) indicates the type of build,
        e.g. release, debug
    :param defines: (optional) list of var=val strings for CMake's -D option
    :param term: (optional) output stream for verbose output
    :param command_log: (optional) capture commands run and their return codes
    :param always_clean: (optional) always remove the build area before build
    """
    build_config = kwargs.pop("build_config", None)
    generator = kwargs.pop("generator", None)
    defines = kwargs.pop("defines", None)
    term = kwargs.pop("term", None)
    always_clean = kwargs.pop("clean", False)

    command_log = kwargs.pop("command_log", None)

    if not os.path.isabs(watch_path):
        raise IOError(errno.EINVAL, "Watch path {} must be absolute".format(watch_path))
    if not os.path.isabs(build_path):
        raise IOError(errno.EINVAL, "Build path {} must be absolute".format(build_path))
    defines = defines if defines else []
    return partial(
        execute,
        [
            partial(cmake_clean, build_path, defines, always_clean),
            partial(
                cmake_generate,
                watch_path,
                build_path,
                build_config,
                generator,
                defines,
            ),
            partial(cmake_build, build_path, build_config),
        ],
        term=term,
        command_log=command_log,
    )


def execute(commands, term=None, command_log=None):
    """Executes the list of callable objects.

    Each callable object is a command generator that when called returns a
    command that can be executed as a subprocess. The command returned will be
    a list for subprocess's non-string form (ie ['ls', '-la'], not 'ls -la')
    to avoid shell escaping mishaps.

    :param commands: a list of callable objects
    :param term: (optional) output stream for verbose output
    :param command_log: (optional) capture commands run and their return codes
    """
    from ttt.subproc import checked_call

    for command_generator in commands:
        command = command_generator()
        if command:  # Note that command may be None (or empty list)
            if term:
                term.writeln("execute: {}".format(command), verbose=1)
            rc = 0
            try:
                rc = checked_call(command, stderr=subprocess.STDOUT)
            except subprocess.CalledProcessError as error:
                rc = error.returncode
            if command_log is not None:
                command_log.append((command, rc))
        else:
            if command_log is not None:
                command_log.append(None)


GENERATED = ["Makefile", "build.ninja", "*.sln"]


def cmake_clean(build_path, defines, always_clean):
    def cmake_build_area_outdated():
        # If cmake had not generated a build file, recreate the build area.
        generated = []
        for f in GENERATED:
            generated += glob.glob(os.path.join(build_path, f))
            if generated:
                break
        if len(generated) == 0:
            return True

        # If the cmake version has changed since the build area was created,
        # recreate it.
        cmake_cache_file = os.path.join(build_path, "CMakeCache.txt")
        if os.path.exists(cmake_cache_file):
            with open(cmake_cache_file, "r") as f:
                for line in f:
                    if "CMAKE_COMMAND:INTERNAL" in line:
                        _, cmake_path = line.rstrip().split("=")
                        if not os.path.exists(cmake_path):
                            return True
                    if "ENABLE_TESTS:BOOL=OFF" in line:
                        for d in defines:
                            if "ENABLE_TESTS" in d:
                                if "ON" in d:
                                    return True
        return False

    if os.path.exists(build_path) and (always_clean or cmake_build_area_outdated()):
        shutil.rmtree(build_path)
    return None


def cmake_generate(watch_path, build_path, build_config, generator, defines):
    """Generates the command for cmake that will create a build area for a
    source tree.

    This creates the Makefile, build.ninja, project.sln, etc for the project.

    If the build area has already been created, then the command is None.

    If the build area has already been created, but the cmake command that
    generated it no longer exists, then the build area is removed first before
    the command is generated.

    :param watch_path: the absolute root directory path of the source tree
        where the CMakeLists.txt file exists
    :param build_path: the absolute root directory path where build objects and
        binaries are output during compilation
    :param build_config: indicates the type of build, e.g. release, debug
    :param generator: (optional) the cmake generator. Values are the same as
        provided by the cmake usage output. e.g. "Unix Makefile", "Ninja"
        This is because it is passed through via the -G option. Not providing
        it is the same as not providing it to the cmake command and will make
        cmake use the default generator for the executing platform
    :param defines: (optional) list of var=val strings for CMake's -D option
    :param clean: (optional) remove build area before build
    :return: command to execute as a subprocess in list form
    """
    cmake_lists_file = os.path.join(watch_path, "CMakeLists.txt")
    if not os.path.exists(cmake_lists_file):
        raise IOError(
            errno.EINVAL, "No CMakeLists.txt detected in {}".format(watch_path)
        )
    if not os.path.exists(os.path.join(build_path, "CMakeFiles")):
        command = ["cmake"]
        if generator is not None:
            command.append("-G")
            command.append(generator)
        command.append("-H{}".format(watch_path))
        command.append("-B{}".format(build_path))
        # this does nothing for the MSVC generator
        if build_config is not None and platform.system() != "Windows":
            command.append("-DCMAKE_BUILD_TYPE={}".format(build_config))
        for define in defines:
            command.append("-D{}".format(define))
        return command


def cmake_build(build_path, build_config):
    """Generates the cmake command to (re)build the build area.

    This is the call to the platform's compiler.

    :param build_path: the absolute root directory path where build objects and
        binaries are output during compilation
    :param build_config: indicates the type of build, e.g. release, debug
    :return: command to execute as a subprocess in list form
    """
    command = [
        "cmake",
        # the order is important. --build must come first
        "--build",
        build_path,
    ]
    if build_config is not None and platform.system() == "Windows":
        # necessary for multi-configuration build systems, e.g. MSVC
        # should be harmless otherwise
        command.append("--config")
        command.append(build_config)
    return command
