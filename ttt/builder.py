import os
import subprocess
import errno


def create_builder(context, watch_path, build_path, generator=None):
    if not os.path.isabs(watch_path):
        raise IOError(
            errno.EINVAL, "Watch path {} must be absolute".format(watch_path)
        )
    if not os.path.isabs(build_path):
        raise IOError(
            errno.EINVAL, "Build path {} must be absolute".format(build_path)
        )
    return CMakeBuilder(context, watch_path, build_path, generator)


class Builder(object):
    pass


class CMakeBuilder(Builder):
    """
    Provides a context in which cmake operations occur.
    This will create a cmake build area for a source area if none exists and
    provide a means to call the build command in that area.
    """

    def __init__(self, context, watch_path, build_path, build_system):
        self.context = context
        self.watch_path = watch_path
        self.build_path = build_path
        self.build_system = build_system

    def build(self):
        """
        Calls the build command in the build area. If no build area exists, it
        will be created.
        """
        if not os.path.exists(os.path.join(self.build_path, 'CMakeFiles')):
            self._cmake_generate()
        self._build()

    def _build(self):
        self._execute([
            'cmake',
            '--build',
            self.build_path
        ])

    def _cmake_generate(self):
        watch_path = self.watch_path
        build_path = self.build_path
        command = ['cmake']
        if self.build_system is not None:
            command.append('-G')
            command.append(self.build_system)
        command.append('-H{}'.format(watch_path))
        command.append('-B{}'.format(build_path))
        self._execute(command)

    def _execute(self, command, cwd=None):
        self.context.checked_call(
            command,
            stderr=subprocess.STDOUT,
            cwd=cwd
        )
