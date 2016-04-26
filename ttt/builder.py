import os
import subprocess
import errno
import shutil
from functools import partial


def create_builder(context, watch_path, build_path, generator=None):
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
        context,
        [
            partial(cmake_generate, watch_path, build_path, generator),
            partial(cmake_build, build_path)
        ]
    )


def execute(context, commands):
    for command_generator in commands:
        command = command_generator()
        if command:
            context.checked_call(command, stderr=subprocess.STDOUT)


def cmake_build(build_path):
    return ['cmake', '--build', build_path]


def cmake_generate(watch_path, build_path, generator):
    # Check that the cmake that created the build area is the available cmake.
    # If not, then the build area has to be regenerated for cmake to continue
    # its build.
    cmake_cache_file = os.path.join(build_path, 'CMakeCache.txt')
    if os.path.exists(cmake_cache_file):
        with open(cmake_cache_file, 'r') as f:
            for line in f:
                if 'CMAKE_COMMAND:INTERNAL' in line:
                    _, cmake_path = line.rstrip().split('=')
                    if not os.path.exists(cmake_path):
                        shutil.rmtree(build_path)
                    break

    if not os.path.exists(os.path.join(build_path, 'CMakeFiles')):
        command = ['cmake']
        if generator:
            command.append('-G')
            command.append(generator)
        command.append('-H{}'.format(watch_path))
        command.append('-B{}'.format(build_path))
        return command
