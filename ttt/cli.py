import argh

from ttt import monitor
from ttt.terminal import Terminal
from . import __version__
import platform

WINGEN = 'Visual Studio 15 2017 Win64'
DEFAULT_GEN = WINGEN if platform.system() is 'Windows' else None

@argh.arg('watch_path', help='Source path to watch.')
@argh.arg('filename', nargs='*', default=monitor.DEFAULT_SOURCE_PATTERNS,
          help='A series of file names or file name patterns to be watched. '
               'These are only meaningful when watch mode is enabled. '
               'When files identified by the file name or file name patterns '
               'are detected to have been added, changed, or deleted, this '
               'triggers a watch, build, test cycle. If not provided, files '
               'matching *.cc, *.c, *.h, and CMakeLists.txt are watched. '
               'Be aware of shell expansion!')
@argh.arg('-b', '--build_path',
          help='Path to the build area. If not provided, it will be in a '
               'directory under the local path named {dir}-{config}-build '
               'where {dir} is the basename of the source path, and {config} '
               'is the build configuration. If provided and is relative, it '
               'will be created under the local path.')
@argh.arg('-v', '--verbosity', default=None, action='count',
          help='More v\'s more verbose.')
@argh.arg('-g', '--generator', default=DEFAULT_GEN,
          help='cmake generator: refer to cmake documentation')
@argh.arg('-c', '--config', default='Debug',
          help='build configuration: e.g. Release, Debug')
@argh.arg('--irc_server', default=None,
          help='IRC server hostname. Requires --watch')
@argh.arg('--irc_port', default=6667,
          help='IRC server port. Requires --irc_server')
@argh.arg('--irc_channel', default=None,
          help='IRC channel. Requires --irc_server')
@argh.arg('--irc_nick',
          help='IRC nick or derived from the watch path and the build '
               'configuration. Requires --irc_server')
@argh.arg('-w', '--watch', default=False,
          help='Enable watch mode - the watch, build, test cycle.')
@argh.arg('-t', '--test', default=False,
          help='Test after build. If given, -DENABLE_TESTS=ON is implied.')
@argh.arg('-D', metavar='VAR=VALUE', dest='define', action='append',
          help='Used like CMake\'s -Dvar=value options. Repeatable.')
@argh.arg('-x', metavar='VAR=VALUE', dest='exclude', action='append',
          help='Exclude files and directories by name or by pattern. '
               'Repeatable.')
def ttt(watch_path, *filename, **kwargs):
    verbosity = kwargs.pop("verbosity", 0)
    Terminal.VERBOSITY = verbosity if verbosity else 0
    patterns = set([''.join(f) for f in filename])  # why join?
    if verbosity:
        print("Watching:")
        for p in patterns:
            print(p)
    m = monitor.create_monitor(watch_path, patterns, **kwargs)

    if kwargs.pop("watch", False):
        m.run()
    else:
        m.build()
        m.test()


def run():
    parser = argh.ArghParser(
        prog='ttt',
        description='Watch, build, and test a cmake enabled source area.'
    )
    parser.add_argument('--version',
                        action='version',
                        version='%(prog)s ' + __version__)
    parser.set_default_command(ttt)
    parser.dispatch()
