import subprocess
import threading
import re
import sys

def read_stream(output_stream, input_stream, io_q):
    if not input_stream:
        io_q.put((output_stream, 'EXIT'))
        return
    for line in input_stream:
        io_q.put((output_stream, line))
    if not input_stream.closed:
        input_stream.close()
    io_q.put((output_stream, 'EXIT'))

def call_output(*popenargs, **kwargs):
    if 'stdout' in kwargs:
        raise ValueError('stdout argument not allowed, it will be overridden.')
    kwargs['stdin'] = subprocess.PIPE

    line_handler = None
    if 'line_handler' in kwargs:
        line_handler = kwargs['line_handler']
        del kwargs['line_handler']

    process = create_process(*popenargs, stdout=subprocess.PIPE, **kwargs)
    return run(process, line_handler)

def create_process(*popenargs, **kwargs):
    return subprocess.Popen(*popenargs, **kwargs)

def run(process, line_handler):
    try:
        from queue import Queue, Empty
    except ImportError:
        from Queue import Queue, Empty
    io_q = Queue(5)
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
        except Empty:
            if process.poll() is not None:
                break
        else:
            outstream, message = item
            if message == 'EXIT':
                del threads[outstream]
            else:
                if line_handler is not None:
                    handled_message = line_handler(message)
                    if handled_message is None:
                        outstream.write(message)
                    else:
                        try:
                            handled_message = handled_message.decode('utf-8')
                        except AttributeError:
                            pass
                        outstream.write(handled_message)
                else:
                    outstream.write(message)
                outstream.flush()

    process.wait()
    return process.returncode
