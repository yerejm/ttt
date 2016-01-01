import argh
import colorama

from ttt import systemcontext
from ttt import monitor

@argh.arg('watch_path', help='Source path to watch.')
@argh.arg('-b', '--build_path', help='Path to the \
        build area. If not provided, it will be in a directory under the local \
        path named {dir}-build where {dir} is the basename of the source path.')
@argh.arg('-v', '--verbosity', action='count', help='More v\'s more verbose.')
def ttt(watch_path, **kwargs):
    context = systemcontext.create_context(**kwargs)
    try:
        monitor.create_monitor(context, watch_path, **kwargs).run()
    except monitor.InvalidWatchArea as e:
        print(e)
        raise

def run():
    colorama.init()
    parser = argh.ArghParser(prog='ttt', description='Watch, build, and test a cmake enabled source area.')
    argh.set_default_command(parser, ttt)
    parser.dispatch()

