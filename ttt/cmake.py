import os
import subprocess
import multiprocessing
import platform
import glob
import collections

BuildSystem = collections.namedtuple('BuildSystem', [
    'file',
    'command',
    'parallel_opt',
    'file_opt',
])
BUILD_SYSTEMS = {
    'Unix Makefiles': BuildSystem(
        file='Makefile',
        command='make',
        parallel_opt='-j{}',
        file_opt='-f{}'
    ),
    'Ninja': BuildSystem(
        file='build.ninja',
        command='ninja',
        parallel_opt='-j{}',
        file_opt='-f{}'
    ),
    'Visual Studio 14 2015': BuildSystem(
        file='*.sln',
        command='msbuild',
        parallel_opt='/m:{}',
        file_opt='{}'
    ),
}
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
        if build_system not in BUILD_SYSTEMS:
            raise InvalidCMakeGenerator()
        self.build_system = build_system
        self.watch_path = os.path.abspath(watch_path)
        self.build_path = make_build_path(watch_path) if build_path is None else build_path
        self.build_system = build_system

    def build_file(self):
        """ Get the build file for the cmake build area, e.g. Makefile."""
        # Cache the build file to avoid repeating path traversal.
        try:
            return self._build_file
        except AttributeError:
            self._build_file = self._find_build_file()
            return self._build_file

    def build_command(self):
        """ Get the build command for the cmake build area, e.g. make."""
        return BUILD_SYSTEMS[self.build_system].command

    def build(self):
        """
        Calls the build command in the build area. If no build area exists, it
        will be created.
        """
        if not os.path.exists(os.path.join(self.build_path, 'CMakeFiles')):
            self._cmake_generate()
            self._build_file = self._find_build_file()
        self._build()

    def _build(self):
        build = BUILD_SYSTEMS[self.build_system]
        old_path = os.getcwd()
        try:
            os.chdir(self.build_path)
            self._execute([
                build.command,
                build.parallel_opt.format(multiprocessing.cpu_count() + 2),
                build.file_opt.format(self._build_file)
            ])
        finally:
            os.chdir(old_path)

    def _find_build_file(self):
        build_file_pattern = BUILD_SYSTEMS[self.build_system].file
        search_path = os.path.join(self.build_path, build_file_pattern)
        print("Search for {}".format(search_path))
        matches = glob.glob(search_path)
        return os.path.basename(matches[0]) if matches else None

    def _cmake_generate(self):
        self._execute([
            'cmake',
            '-G', self.build_system,
            '-H{}'.format(self.watch_path),
            '-B{}'.format(self.build_path)
        ])

    def _execute(self, command):
        try:
            subprocess.check_call(command, stderr=subprocess.STDOUT, universal_newlines=True)
        except subprocess.CalledProcessError as e:
            raise CMakeError(command)

class CMakeError(Exception):
    """ Exception raised when a cmake command fails."""

    def __init__(self, command):
        self.command = command

    def __str__(self):
        return '{}'.format(repr(self.command))

class InvalidCMakeGenerator(Exception):
    """ Exception raised for a generator that is invalid on the current
    platform."""
    pass

