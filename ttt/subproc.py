import subprocess
import threading
import re
import sys
from six.moves import queue


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
