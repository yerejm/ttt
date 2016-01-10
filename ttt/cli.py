import argh

from ttt import systemcontext
from ttt import monitor


@argh.arg('watch_path', help='Source path to watch.')
@argh.arg('-b', '--build_path',
          help='Path to the build area. If not provided, it will be in a '
               'directory under the local path named {dir}-build where {dir} '
               'is the basename of the source path. If provided and is '
               'relative, it will be created under the local path.')
@argh.arg('-v', '--verbosity', action='count',
          help='More v\'s more verbose.')
@argh.arg('-g', '--generator',
          help='cmake generator: refer to cmake documentation')
def ttt(watch_path, **kwargs):
    context = systemcontext.create_context(**kwargs)
    monitor.create_monitor(context, watch_path, **kwargs).run()


def run():
    parser = argh.ArghParser(
        prog='ttt',
        description='Watch, build, and test a cmake enabled source area.'
    )
    parser.set_default_command(ttt)
    parser.dispatch()
