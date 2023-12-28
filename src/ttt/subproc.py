"""
ttt.subproc
~~~~~~~~~~~~
This module provides additional functions for subprocess execution built on top
of the existing subprocess module.

:copyright: (c) yerejm
"""

import os
import queue
import subprocess
import sys
import threading


def execute(*args, **kwargs):
    """Wrapper around subprocess.check_output where the universal newlines
    option is enabled.

    Otherwise, operates the same as that function.
    """
    kwargs["universal_newlines"] = True
    return subprocess.check_output(*args, **kwargs).splitlines()


def checked_call(*args, **kwargs):
    """Wrapper around subprocess.checked_call where the universal newlines
    option is enabled.

    Otherwise, operates the same as that function.
    """
    kwargs["universal_newlines"] = True
    return subprocess.check_call(*args, **kwargs)


def streamed_call(*args, **kwargs):
    """A subprocess.call where output can be sent to the caller in real time.

    Arguments to subprocess.Popen are applicable to streamed_call with a few
    differences.

    To receive the lines of output, an object specified for the listener
    keywork argument that must provide the interface fn(channel, message),
    where channel is the where the message was sent (e.g. stdout, stderr), and
    message is the line of output without the platform line end.

    Due to the nature of this call, keywork arguments stdout and stdin cannot
    be provided.

    Universal newline handling is forced.

    :param listener: (optional) an object that consumes the output from the
    executing subprocess.
    :return (process.returncode, stdout list, stderr list) tuple
    """
    kwargs["universal_newlines"] = True
    return call_output(*args, **kwargs)


#
# The following functions should not be used directly.
# They play with threads.
#


def call_output(*popenargs, **kwargs):
    """A custom version of subprocess.call_output() that operates in the same
    way except it allows the optional provision of a callback that is called
    for each line of output emitted by the subprocess.
    """

    def create_process(*popenargs, **kwargs):
        return subprocess.Popen(*popenargs, **kwargs)

    if "stdout" in kwargs:
        raise ValueError("stdout argument not allowed, it will be overridden.")
    if "stdin" in kwargs:
        raise ValueError("stdin argument not allowed, it will be overridden.")

    kwargs["stdin"] = subprocess.PIPE
    line_handler = kwargs.pop("listener", None)

    with create_process(
        *popenargs, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, **kwargs
    ) as process:
        return run(process, line_handler)


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
        "stdout": threading.Thread(
            target=read_stream, args=("stdout", process.stdout, io_q)
        ),
        "stderr": threading.Thread(
            target=read_stream, args=("stderr", process.stderr, io_q)
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
            if message == "EXIT":
                threads[outstream].join()
                del threads[outstream]
            else:
                message = message.rstrip(os.linesep)
                channel = sys.stdout if outstream == "stdout" else sys.stderr
                (stdout if outstream == "stdout" else stderr).append(message)
                if line_handler is not None:
                    line_handler(channel, message)
                else:
                    channel.write(message)
                    channel.flush()

    for t in threads.values():
        t.join()
    process.wait()
    return (process.returncode, stdout, stderr)


def read_stream(stream_name, input_stream, io_q):
    """Captures lines incoming on the input stream on a queue.

    This function is intended to be the function executed by a thread.

    :param stream_name: the name of the stream being read
    :param input_stream: the stream being read
    :param io_q: the queue on to which lines from the input_stream are added.
    It is intended to be a shared data structure between multiple threads of
    execution (primarily between the main thread and the thread executing this
    function).
    """
    if not input_stream:
        io_q.put((stream_name, "EXIT"))
        return
    for line in input_stream:
        io_q.put((stream_name, line))
    if not input_stream.closed:
        input_stream.close()
    io_q.put((stream_name, "EXIT"))
