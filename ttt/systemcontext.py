import os
import sys
import stat
import subprocess
import threading
from six.moves import queue

try:
    from os import scandir, walk
except ImportError:
    try:
        from scandir import scandir, walk
    except ImportError:
        from os import walk

EXCLUSIONS = set([ '.git', '.hg' ])
class SystemContext(object):
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

    process = create_process(*popenargs, stdout=subprocess.PIPE, **kwargs)
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
    threads = {}
    threads[sys.stdout] = threading.Thread(
        target=read_stream,
        args=(sys.stdout, process.stdout, io_q)
    ).start()

    threads[sys.stderr] = threading.Thread(
        target=read_stream,
        args=(sys.stderr, process.stderr, io_q)
    ).start()

    while threads:
        try:
            item = io_q.get(True, 1)
        except queue.Empty:
            if process.poll() is not None:
                break
        else:
            outstream, message = item
            if message == 'EXIT':
                del threads[outstream]
            else:
                if line_handler is not None:
                    line_handler(message)
                else:
                    outstream.write(message)
                    outstream.flush()

    process.wait()
    return process.returncode

