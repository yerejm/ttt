import argh

from ttt import monitor
from ttt.terminal import Terminal
from . import __version__


@argh.arg('watch_path', help='Source path to watch.')
@argh.arg('-b', '--build_path',
          help='Path to the build area. If not provided, it will be in a '
               'directory under the local path named {dir}-{config}-build '
               'where {dir} is the basename of the source path, and {config} '
               'is the build configuration. If provided and is relative, it '
               'will be created under the local path.')
@argh.arg('-v', '--verbosity', default=None, action='count',
          help='More v\'s more verbose.')
@argh.arg('-g', '--generator', default=None,
          help='cmake generator: refer to cmake documentation')
@argh.arg('-c', '--config', default='debug',
          help='build configuration: e.g. release, debug')
@argh.arg('--irc_server', default=None,
          help='IRC server hostname. Requires --watch')
@argh.arg('--irc_port', default=6667,
          help='IRC server port. Requires --irc_server')
@argh.arg('--irc_channel', default='#ttt',
          help='IRC channel. Requires --irc_server')
@argh.arg('--irc_nick',
          help='IRC nick or derived from the watch path and the build '
               'configuration. Requires --irc_server')
@argh.arg('--watch', default=False,
          help='Enable the watch, build, test cycle.')
@argh.arg('--test', default=False,
          help='Test after build.')
def ttt(watch_path, **kwargs):
    verbosity = kwargs.pop("verbosity", 0)
    Terminal.VERBOSITY = verbosity if verbosity else 0
    m = monitor.create_monitor(watch_path, **kwargs)

    if kwargs.pop("watch", False):
        m.run()
    else:
        m.build()
        if kwargs.pop("test", False):
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
