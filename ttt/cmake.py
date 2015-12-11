import os
import subprocess
import multiprocessing
import platform
import glob
import collections

from ttt import subproc

DEFAULT_BUILD_WINDOWS = 'Visual Studio 14 2015'
DEFAULT_BUILD_UNIX = 'Unix Makefiles'
DEFAULT_BUILD_PATH_SUFFIX = '-build'

def default_build_system():
    default = DEFAULT_BUILD_UNIX
    if platform.system() is 'Windows':
        DEFAULT_BUILD_WINDOWS
    return default

def make_build_path(watch_path, suffix=DEFAULT_BUILD_PATH_SUFFIX):
    return os.path.join(
        os.getcwd(),
        "{}{}".format(os.path.basename(watch_path), suffix)
    )

class CMakeContext(object):
    """
    Provides a context in which cmake operations occur.
    This will create a cmake build area for a source area if none exists and
    provide a means to call the build command in that area.
    """

    def __init__(self, watch_path, build_path=None, build_system=default_build_system()):
        self.watch_path = os.path.abspath(watch_path)
        self.build_path = make_build_path(watch_path) if build_path is None else build_path
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
        self._execute([
            'cmake',
            '-G', self.build_system,
            '-H{}'.format(self.watch_path),
            '-B{}'.format(self.build_path)
        ])

    def _execute(self, command, cwd=None):
        try:
            subprocess.check_call(
                command,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
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

