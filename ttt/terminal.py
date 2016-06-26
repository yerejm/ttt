"""
ttt.terminal
~~~~~~~~~~~~
This module handles output to the terminal that is executing ttt.

The terminal could be a UNIX terminal, or the Windows command.exe or
powershell.exe.

:copyright: (c) yerejm
"""
import os
from six import text_type

# When writing to output streams, do not write more than the following width.
TERMINAL_MAX_WIDTH = 78


class Terminal(object):
    # Yes, this is a global variable...
    VERBOSITY = 0

    """A Terminal that will write lines given to it to an output stream."""
    def __init__(self, stream=None, verbosity=None):
        """Creates a terminal for a specific verbosity.

        :param stream: (optional) the output stream to send output. By default,
        the output is discarded.
        :param verbosity: (optional) sets the verbosity required for lines need
        to be set at for output to occur. Default is 0, which is the default
        for lines that do not specify a verbosity.
        """
        self._verbosity = verbosity if verbosity else Terminal.VERBOSITY
        self.stream = stream

    def write(self, string):
        """Writes a string to the output stream."""
        stream = self.stream
        if stream:
            stream.write(text_type(string))
            stream.flush()

    def writeln(self, *args, **kwargs):
        """Output all unnamed arguments as a single line to the output stream.

        :param *args: variadic list of objects to be output in string form
        :param verbose: (optional) the verbosity level of the line output.
        Default is 0, which is the default verbosity of the Terminal.
        :param end: (optional) the line end character. Default is the platform
        specific line end.
        :param decorator: (optional) list of functions to be executed on the
        final string before output. The order of the functions in the list is
        the order that the functions are applied to the final string.
        :param pad: (optional) a string that is repeatedly used to pad the
        final string up to a given width (see width parameter).
        :param width: (optional) the width of the final line to be output. If
        the line is too short, it is padded with the pad string (see pad
        parameter). Default width is 78. The maximum width is 78.
        """
        level = kwargs.pop('verbose', 0)
        end = kwargs.pop('end', None)
        decorator = kwargs.pop('decorator', None)
        pad = kwargs.pop('pad', None)
        width = kwargs.pop('width', None)

        if level == self._verbosity:
            line = "".join([str(a) for a in args])
            if width and not pad:
                raise Exception('An empty pad cannot be provided with a '
                                'non-zero width')
            if pad:
                line = pad_line(line, pad,
                                term_width() if width is None else width)
            if decorator:
                for d in decorator:
                    line = d(line)
            self.write(line + (os.linesep if end is None else end))


def term_width():
    """Get the width of the terminal if possible.

    Assumes a width of 78 if not possible.
    """
    try:
        from shutil import get_terminal_size
        ts = get_terminal_size()
        return ts.columns
    except ImportError:
        return TERMINAL_MAX_WIDTH


def pad_line(string, pad, width):
    """Pads a string to the given width with the given pad string such that the
    string is centered between the padding (separated on each side by a single
    space). When the amount of padding on either side cannot be the same, the
    padding favours the right side with the extra padding.

    :param pad: the padding string
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
    if pad_width == 0:
        return string

    strlen = len(string) + 2
    total_padlen = pad_width - strlen
    left_padlen = int(total_padlen / 2)
    right_padlen = total_padlen - left_padlen

    return "{} {} {}".format(
        ''.ljust(left_padlen, pad),
        string,
        ''.ljust(right_padlen, pad)
    )
