import os
import subprocess
import errno
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
    if not os.path.exists(os.path.join(build_path, 'CMakeFiles')):
        command = ['cmake']
        if generator:
            command.append('-G')
            command.append(generator)
        command.append('-H{}'.format(watch_path))
        command.append('-B{}'.format(build_path))
        return command
