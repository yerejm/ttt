import subprocess
import threading
import re
import sys

def read_stream(stream_id, stream, io_q):
    if not stream:
        io_q.put((stream_id, 'EXIT'))
        return
    for line in stream:
        io_q.put((stream_id, line))
    if not stream.closed:
        stream.close()
    io_q.put((stream_id, 'EXIT'))

def call_output(*popenargs, **kwargs):
    if 'stdout' in kwargs:
        raise ValueError('stdout argument not allowed, it will be overridden.')
    kwargs['stdin'] = subprocess.PIPE

    return run(*popenargs, stdout=subprocess.PIPE, **kwargs)

def run(*popenargs, **kwargs):

    try:
        from queue import Queue, Empty
    except ImportError:
        from Queue import Queue, Empty
    io_q = Queue(5)
    threads = {}
    process = subprocess.Popen(*popenargs, **kwargs)
    threads['stdout'] = threading.Thread(
        target=read_stream,
        name='stdout',
        args=('stdout', process.stdout, io_q)
    ).start()

    threads['stderr'] = threading.Thread(
        target=read_stream,
        name='stderr',
        args=('stderr', process.stderr, io_q)
    ).start()

    stdout_output = []
    stderr_output = []
    ansi_escape = re.compile(r'')
    while threads:
        try:
            item = io_q.get(True, 1)
        except Empty:
            if process.poll() is not None:
                break
        else:
            stream_id, message = item
            if message == 'EXIT':
                del threads[stream_id]
            else:
                raw_message = ansi_escape.sub('', message)
                if stream_id == 'stdout':
                    outstream = sys.stdout
                    stdout_output.append(raw_message)
                elif stream_id == 'stderr':
                    outstream = sys.stderr
                    stderr_output.append(raw_message)
                outstream.write(message)
                outstream.flush()

    process.wait()

    retcode = process.returncode
    stdout = ''.join(stdout_output)
    stderr = ''.join(stderr_output)
    if retcode:
        try:
            args = process.args
            raise subprocess.CalledProcessError(retcode, args,
                                     output=stdout, stderr=stderr)
        except AttributeError:
            args = popenargs[0]
            raise subprocess.CalledProcessError(retcode, args,
                                     output=stdout)
    return stdout
