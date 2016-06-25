"""
ttt.systemcontext
~~~~~~~~~~~~
This module implements abstractions to try to hide operating system and python
specifics from higher level modules.
:copyright: (c) yerejm
"""
import os
import sys
import subprocess
import threading
from six.moves import queue


class SystemContext(object):
    """Hides the operating system level functionality from higher levels."""
    def __init__(self, verbosity=0):
        self._verbosity = verbosity

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
    """A custom version of subprocess.call_output() that operates in the same
    way except it allows the optional provision of a callback that is called
    for each line of output emitted by the subprocess.
    """
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
        stderr=subprocess.STDOUT,
        **kwargs
    )
    return run(process, line_handler)


def read_stream(stream_name, input_stream, io_q):
    """Captures lines incoming on the input stream on a queue.

    This queue in intended to be a shared data structure between threads.

    :param stream_name: the name of the stream being read
    :param input_stream: the stream being read
    :param io_q: the queue on to which lines from the input_stream are added
    """
    if not input_stream:
        io_q.put((stream_name, 'EXIT'))
        return
    for line in input_stream:
        io_q.put((stream_name, line))
    if not input_stream.closed:
        input_stream.close()
    io_q.put((stream_name, 'EXIT'))


def run(process, line_handler):
    """Maintains the process being executed in a subprocess until it ends.

    Lines of output being emitted by the process are send to the lin handler if
    any.

    Communication between the process executing run() and the subprocess is
    handled by threads reading from the stdout and stderr streams. Threads are
    required to read the output as it is emitted by the subprocess in real-time
    or else it would block until the subprocess had ended.
    """

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
    # Unfortunately, stdout and stderr are not synchronised with each other.
    # This makes capturing both for real-time processing useless. So it is
    # currently all captured under stdout. Even more unfortunately, stderr
    # comes through first before stdout. This means writes that are made first
    # to stdout will not be first through the pipe if there is stderr output.
    #
    # This lack of sychronisation between stdout and stderr output makes
    # real-time display useless because they aren't captured and passed
    # through to the handler as they are encountered.
    #
    # Worse still, there appear to be issues with subprocess output capture on
    # Windows.
    #
    # A proper resolution would be to provide a custom subprocess module but
    # since the common usage does not require real-time capture of
    # stdout/stderr, this is not worth the effort. Manually running whatever
    # was intended for the subprocess outside ttt is the only recourse.
    #
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
