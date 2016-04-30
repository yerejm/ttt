"""
ttt.systemcontext
~~~~~~~~~~~~
This module implements abstractions to try to hide operating system and python
specifics from higher level modules.
:copyright: (c) yerejm
"""
import platform
import os
import sys
import stat
import subprocess
import threading
from six.moves import queue
from six import text_type

# Pick the better timer for the platform
if platform.system() == 'Windows':
    from time import clock as timer
else:
    from time import time as timer

# Pick the better scandir for the python
try:
    from os import scandir, walk
except ImportError:
    try:
        from scandir import scandir, walk  # noqa
    except ImportError:
        from os import walk

# When writing to output streams, do not write more than the following width.
TERMINAL_MAX_WIDTH = 78
# When traversing a directory tree, do not enter the following directories
EXCLUSIONS = set(['.git', '.hg'])


class SystemContext(object):
    """Hides the operating system level functionality from higher levels."""
    def __init__(self, verbosity=0):
        self._verbosity = verbosity

    def walk(self, root_directory):
        for dirpath, dirlist, filelist in walk(root_directory, topdown=True):
            dirlist[:] = [d for d in dirlist if d not in EXCLUSIONS]
            for filename in filelist:
                path = os.path.join(dirpath, filename)
                filestat = os.stat(path)
                if stat.S_ISREG(filestat.st_mode):
                    yield (
                        dirpath,
                        filename,
                        filestat.st_mode,  # file permissions
                        filestat.st_mtime  # last modified time
                    )

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
                    width = (
                        kwargs['width'] if 'width' in kwargs else term_width()
                    )
                    string = pad(kwargs['pad'], string, width)
                if 'decorator' in kwargs:
                    for d in kwargs['decorator']:
                        string = d(string)
                self.write(string + line_end)
        else:
            self.write(line_end)


def term_width():
    """Get the width of the terminal if possible. Defaults to 78."""
    try:
        from shutil import get_terminal_size
        ts = get_terminal_size()
        return ts.columns
    except ImportError:
        return TERMINAL_MAX_WIDTH


def pad(padchar, string, width):
    """Pads a string to the given width with the given character such that the
    string is centered between the padding (separated on each side by a single
    space). When the amount of padding on either side cannot be the same, the
    padding favours the right side with the extra padding.

    :param padchar: the padding character
    :param string: the string to be padded on the left and right with the
        padding character
    :param width: the desired width of the padded string. The width is capped
        to the maximum width of 78.
    :return the padded string

      >>> pad('*', 'hello', 10)
      '* hello **'
      >>> pad('*', 'hello', 11)
      '** hello **'
    """
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


class Timer(object):
    """Self-capturing time keeper intended for use by the 'with' idiom."""
    def __enter__(self):
        self.start = timer()
        return self

    def __exit__(self, *args):
        self.end = timer()
        self.secs = self.end - self.start
