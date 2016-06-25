import argh

from ttt.systemcontext import SystemContext
from ttt import monitor
from . import __version__


@argh.arg('watch_path', help='Source path to watch.')
@argh.arg('-b', '--build_path',
          help='Path to the build area. If not provided, it will be in a '
               'directory under the local path named {dir}-{config}-build '
               'where {dir} is the basename of the source path, and {config} '
               'is the build configuration. If provided and is relative, it '
               'will be created under the local path.')
@argh.arg('-v', '--verbosity', action='count', default=0,
          help='More v\'s more verbose.')
@argh.arg('-g', '--generator', default=None,
          help='cmake generator: refer to cmake documentation')
@argh.arg('-c', '--config',
          help='build configuration: e.g. release, debug', default='debug')
@argh.arg('--irc_server', default=None, help='IRC server hostname.')
@argh.arg('--irc_port', help='IRC server port.', default=6667)
@argh.arg('--irc_channel', help='IRC channel.', default='#ttt')
@argh.arg('--irc_nick',
          help='IRC nick derived from the watch path and the build '
               'configuration.')
def ttt(watch_path, **kwargs):
    context = SystemContext(kwargs['verbosity'])
    monitor.create_monitor(context, watch_path, **kwargs).run()


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
