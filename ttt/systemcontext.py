import time
import platform
import os
import sys
import stat
import subprocess
import threading
from six.moves import queue
from six import text_type

if platform.system() == 'Windows':
    from time import clock as time
else:
    from time import time

try:
    from os import scandir, walk
except ImportError:
    try:
        from scandir import scandir, walk
    except ImportError:
        from os import walk

TERMINAL_MAX_WIDTH = 80
EXCLUSIONS = set([ '.git', '.hg' ])

def create_context(**kwargs):
    context_kwargs = {}
    if 'verbosity' in kwargs and kwargs['verbosity']:
        context_kwargs['verbosity'] = kwargs['verbosity']
    return SystemContext(**context_kwargs)

class SystemContext(object):
    def __init__(self, **kwargs):
        self._verbosity = kwargs['verbosity'] if 'verbosity' in kwargs else 0

    def walk(self, root_directory):
        for dirpath, dirlist, filelist in walk(root_directory, topdown=True):
            dirlist[:] = [ d for d in dirlist if d not in EXCLUSIONS ]
            for filename in filelist:
                path = os.path.join(dirpath, filename)
                statmode = os.stat(path).st_mode
                if stat.S_ISREG(statmode):
                    yield dirpath, filename, statmode

    def execute(self, *args, **kwargs):
        kwargs['universal_newlines'] = True
        return subprocess.check_output(*args, **kwargs).splitlines()

    def checked_call(self, *args, **kwargs):
        kwargs['universal_newlines'] = True
        return subprocess.check_call(*args, **kwargs)

    def streamed_call(self, *args, **kwargs):
        kwargs['universal_newlines'] = True
        return call_output(*args, **kwargs)

    def write(self, string):
        sys.stdout.write(text_type(string))
        sys.stdout.flush()

    def writeln(self, *args, **kwargs):
        verbosity = kwargs['verbose'] if 'verbose' in kwargs else None
        if verbosity is not None and verbosity != self._verbosity:
            return

        line_end = kwargs['end'] if 'end' in kwargs else os.linesep
        if args:
            for string in args:
                string = str(string)
                if 'pad' in kwargs:
                    width = kwargs['width'] if 'width' in kwargs else term_width()
                    string = pad(kwargs['pad'], string, width)
                if 'decorator' in kwargs:
                    for d in kwargs['decorator']:
                        string = d(string)
                self.write(string + line_end)
        else:
            self.write(line_end)

def term_width():
    try:
        from shutil import get_terminal_size
        ts = get_terminal_size()
        return ts.columns
    except ImportError:
        return TERMINAL_MAX_WIDTH

def pad(padchar, string, width):
    pad_width = min(width, TERMINAL_MAX_WIDTH)
    strlen = len(string) + 2
    total_padlen = pad_width - strlen
    left_padlen = int(total_padlen / 2)
    right_padlen = total_padlen - left_padlen

    return "{} {} {}".format(
            ''.ljust(left_padlen, padchar),
            string,
            ''.ljust(right_padlen, padchar)
        )

def call_output(*popenargs, **kwargs):
    def create_process(*popenargs, **kwargs):
        return subprocess.Popen(*popenargs, **kwargs)

    if 'stdout' in kwargs:
        raise ValueError('stdout argument not allowed, it will be overridden.')
    if 'stdin' in kwargs:
        raise ValueError('stdin argument not allowed, it will be overridden.')

    kwargs['stdin'] = subprocess.PIPE

    line_handler = None
    if 'listener' in kwargs:
        line_handler = kwargs['listener']
        del kwargs['listener']

    process = create_process(
            *popenargs,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            **kwargs
        )
    return run(process, line_handler)

def run(process, line_handler):
    def read_stream(output_stream, input_stream, io_q):
        if not input_stream:
            io_q.put((output_stream, 'EXIT'))
            return
        for line in input_stream:
            io_q.put((output_stream, line))
        if not input_stream.closed:
            input_stream.close()
        io_q.put((output_stream, 'EXIT'))

    io_q = queue.Queue(5)
    threads = {
        'stdout': threading.Thread(
            target=read_stream,
            args=('stdout', process.stdout, io_q)
        ),
        'stderr': threading.Thread(
            target=read_stream,
            args=('stderr', process.stderr, io_q)
        ),
    }

    for thread in threads.values():
        thread.start()

    stdout = []
    stderr = []
    while threads:
        try:
            item = io_q.get(True, 1)
        except queue.Empty:
            if process.poll() is not None:
                break
        else:
            outstream, message = item
            if message == 'EXIT':
                threads[outstream].join()
                del threads[outstream]
            else:
                message = message.rstrip(os.linesep)
                channel = sys.stdout if outstream == 'stdout' else sys.stderr
                (stdout if outstream == 'stdout' else stderr).append(message)
                if line_handler is not None:
                    line_handler(channel, message)
                else:
                    channel.write(message)
                    channel.flush()

    for t in threads.values():
        t.join()
    process.wait()
    return (process.returncode, stdout, stderr)

class Timer(object):
    def __enter__(self):
        self.start = time()
        return self

    def __exit__(self, *args):
        self.end = time()
        self.secs = self.end - self.start

