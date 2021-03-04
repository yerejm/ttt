"""
ttt.terminal
~~~~~~~~~~~~
This module handles output to the terminal that is executing ttt.

The terminal could be a UNIX terminal, or the Windows command.exe or
powershell.exe.

:copyright: (c) yerejm
"""
from datetime import datetime, timedelta
import os
import sys

from six import text_type
import termstyle

from ttt.executor import CRASHED, FAILED
from ttt.reporter import Reporter
from . import __version__

# When writing to output streams, do not write more than the following width.
TERMINAL_MAX_WIDTH = 78


def DEFAULT_TIMESTAMP():
    return datetime.now().strftime("%d/%m/%Y %H:%M:%S")


class TerminalReporter(Reporter):
    def __init__(
        self, watch_path, build_path, terminal=None, timestamp=DEFAULT_TIMESTAMP
    ):
        self.terminal = terminal if terminal else Terminal(stream=sys.stdout)
        self.watch_path = watch_path
        self.build_path = build_path
        self.timestamp = timestamp

    def session_start(self, session_descriptor):
        self.writeln(
            "{} session starts".format(session_descriptor),
            decorator=[termstyle.bold],
            pad="=",
        )

    def session_end(self, session_descriptor, duration=None):
        s = "{} session ends".format(session_descriptor)
        if duration is not None:
            s += "; time to complete: {}".format(timedelta(seconds=duration))
        self.writeln(s, decorator=[termstyle.bold], pad="=")

    def report_build_path(self):
        self.writeln(
            "### Building:   {}".format(self.build_path), decorator=[termstyle.bold]
        )

    def report_watchstate(self, watchstate):
        def report_changes(change, filelist, decorator):
            for f in filelist:
                self.writeln(
                    "# {} {}".format(change, f),
                    decorator=([] if decorator is None else decorator),
                )

        report_changes("CREATED", watchstate.inserts, [termstyle.green])
        report_changes("MODIFIED", watchstate.updates, [termstyle.yellow])
        report_changes("DELETED", watchstate.deletes, [termstyle.red])
        self.writeln("### Scan time: {:10.3f}s".format(watchstate.walk_time))

    def report_interrupt(self, interrupt):
        self.writeln(interrupt.__class__.__name__, pad="!")

    def wait_change(self):
        self.writeln("waiting for changes", decorator=[termstyle.bold], pad="#")
        self.writeln(
            "### Since:      {}".format(self.timestamp()), decorator=[termstyle.bold]
        )
        self.writeln(
            "### Watching:   {}".format(self.watch_path), decorator=[termstyle.bold]
        )
        self.writeln(
            "### Build at:   {}".format(self.build_path), decorator=[termstyle.bold]
        )
        self.writeln(
            "### Using ttt:  {}".format(__version__), decorator=[termstyle.bold]
        )

    def report_results(self, results):
        shortstats = "{} passed in {} seconds".format(
            results["total_passed"], results["total_runtime"]
        )
        total_failed = results["total_failed"]
        if total_failed > 0:
            self.report_failures(results["failures"])
            self.writeln(
                "{} failed, {}".format(total_failed, shortstats),
                decorator=[termstyle.red, termstyle.bold],
                pad="=",
            )
        else:
            self.writeln(
                shortstats, decorator=[termstyle.green, termstyle.bold], pad="="
            )

    def report_failures(self, results):
        self.writeln("FAILURES", pad="=")
        for testname, out, _err, outcome in results:
            self.writeln(testname, decorator=[termstyle.red, termstyle.bold], pad="_")
            extra_out = []
            if outcome == FAILED:
                test_output_pos = find_source_file_line(out, self.watch_path)
                results = out[test_output_pos:]
                extra_out = out[:test_output_pos]
            elif outcome == CRASHED:
                results = out[1:]
            self.writeln(os.linesep.join(results))

            if extra_out:
                self.writeln("Additional output", pad="-")
                self.writeln(os.linesep.join(extra_out))

            trailer = ""
            if outcome == FAILED:
                if self.watch_path is None:
                    locator = results[0]
                else:
                    locator = strip_path(results[0], self.watch_path)
                trailer = strip_trailer(locator)
            elif outcome == CRASHED:
                trailer = " !!! {} !!!".format(out[0])

            self.writeln(trailer, decorator=[termstyle.red, termstyle.bold], pad="_")

    def interrupt_detected(self):
        self.writeln()
        self.writeln("Interrupt again to exit.")

    def halt(self):
        self.writeln()
        self.writeln("Watching stopped.")

    def writeln(self, *args, **kwargs):
        self.terminal.writeln(*args, **kwargs)


def strip_path(string, path):
    realpath = path
    if realpath not in string:
        realpath = os.path.realpath(path)
    if realpath in string:
        return string[len(realpath) + 1 :]
    else:
        return string


def find_source_file_line(lines, path):
    if path is not None:
        for i, l in enumerate(lines):
            if path in l:
                return i
    return 0


def strip_trailer(string):
    return string[: string.find(" ") - 1]


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
        self.verbosity = verbosity if verbosity else Terminal.VERBOSITY
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
        Default is 0, which is the default verbosity of the Terminal. Output of
        levels at and below the terminal verbosity level will be printed.
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
        level = kwargs.pop("verbose", 0)
        end = kwargs.pop("end", None)
        decorator = kwargs.pop("decorator", None)
        pad = kwargs.pop("pad", None)
        width = kwargs.pop("width", None)

        if level <= self.verbosity:
            line = "".join([str(a) for a in args])
            if width and not pad:
                raise Exception(
                    "An empty pad cannot be provided with a " "non-zero width"
                )
            if pad:
                line = pad_line(line, pad, term_width() if width is None else width)
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
        "".ljust(left_padlen, pad), string, "".ljust(right_padlen, pad)
    )


global_term = Terminal(stream=sys.stdout)
