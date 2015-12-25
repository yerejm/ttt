import os
import subprocess

class CMakeContext(object):
    """
    Provides a context in which cmake operations occur.
    This will create a cmake build area for a source area if none exists and
    provide a means to call the build command in that area.
    """

    def __init__(self, context, build_system=None):
        self.context = context
        self.build_system = build_system

    def build(self, watch_path, build_path):
        """
        Calls the build command in the build area. If no build area exists, it
        will be created.
        """
        if not os.path.exists(os.path.join(build_path, 'CMakeFiles')):
            self._cmake_generate(watch_path, build_path)
        self._build(build_path)

    def _build(self, build_path):
        self._execute([
            'cmake',
            '--build',
            build_path
        ])

    def _cmake_generate(self, watch_path, build_path):
        command = ['cmake']
        if self.build_system is not None:
            command.append('-G')
            command.append(self.build_system)
        command.append('-H{}'.format(watch_path))
        command.append('-B{}'.format(build_path))
        self._execute(command)

    def _execute(self, command, cwd=None):
        try:
            self.context.checked_call(
                command,
                stderr=subprocess.STDOUT,
                cwd=cwd
            )
        except subprocess.CalledProcessError as e:
            raise CMakeError(command)

class CMakeError(Exception):
    """ Exception raised when a cmake command fails."""

    def __init__(self, command):
        self.command = command

    def __str__(self):
        return '{}'.format(repr(self.command))

