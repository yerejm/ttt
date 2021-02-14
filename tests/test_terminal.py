from contextlib import contextmanager
import io
from os import linesep
import sys

from termstyle import bold, red

from ttt.terminal import Terminal


class TestTerminal:
    def test_write(self):
        f = io.StringIO()
        t = Terminal(stream=f)
        t.write("hello")
        assert f.getvalue() == "hello"

    def test_writeln(self):
        f = io.StringIO()
        t = Terminal(stream=f)
        t.writeln()
        assert f.getvalue() == linesep

        f = io.StringIO()
        t = Terminal(stream=f)
        t.writeln("hello")
        assert f.getvalue() == "hello" + linesep

        f = io.StringIO()
        t = Terminal(stream=f)
        t.writeln("hello", 1)
        assert f.getvalue() == "hello1" + linesep

        f = io.StringIO()
        t = Terminal(stream=f)
        t.writeln("hello", "world")
        assert f.getvalue() == "helloworld" + linesep

    def test_writeln_verbosity(self):
        f = io.StringIO()
        t = Terminal(stream=f, verbosity=1)
        t.writeln("hello", verbose=2)
        assert f.getvalue() == ""

        f = io.StringIO()
        t = Terminal(stream=f, verbosity=1)
        t.writeln("hello", verbose=1)
        assert f.getvalue() == "hello" + linesep

        f = io.StringIO()
        t = Terminal(stream=f, verbosity=1)
        t.writeln("hello")
        assert f.getvalue() == "hello" + linesep

        f = io.StringIO()
        t = Terminal(stream=f)
        t.writeln("2", verbose=2)
        t.writeln("1", verbose=1)
        t.writeln("hello")
        assert f.getvalue() == "hello" + linesep

    def test_writeln_line_end(self):
        f = io.StringIO()
        t = Terminal(stream=f)
        t.writeln("hello", end="")
        assert f.getvalue() == "hello"

    def test_writeln_padding(self):
        f = io.StringIO()
        t = Terminal(stream=f)
        t.writeln("hello", pad=".", width=15)
        assert f.getvalue() == ".... hello ...." + linesep

        f = io.StringIO()
        t = Terminal(stream=f)
        t.writeln("hello", "world", pad=".", width=15)
        assert f.getvalue() == ". helloworld .." + linesep

        f = io.StringIO()
        t = Terminal(stream=f)
        t.writeln("hello", pad="")
        assert f.getvalue() == "hello" + linesep

        f = io.StringIO()
        t = Terminal(stream=f)
        raised = False
        try:
            t.writeln("hello", pad="", width=15)
        except Exception as e:
            raised = e
        assert raised

    def test_writeln_padding_default_width(self):
        f = io.StringIO()
        t = Terminal(stream=f)
        t.writeln("hello", pad=".")
        assert f.getvalue() == (
            "".ljust(35, ".") + " hello " + "".ljust(36, ".") + linesep
        )

        f = io.StringIO()
        t = Terminal(stream=f)
        t.writeln("hello", pad=".", width=0)
        assert f.getvalue() == "hello" + linesep

        f = io.StringIO()
        t = Terminal(stream=f)
        t.writeln("hello", pad=".", width=200)
        assert f.getvalue() == (
            "".ljust(35, ".") + " hello " + "".ljust(36, ".") + linesep
        )

    def test_writeln_decorator(self):
        f = io.StringIO()
        t = Terminal(stream=f)
        t.writeln("hello", decorator=[bold])
        assert f.getvalue() == bold("hello") + linesep

        f = io.StringIO()
        t = Terminal(stream=f)
        t.writeln("hello", decorator=[bold, red])
        assert f.getvalue() == red(bold("hello")) + linesep


@contextmanager
def stdout_redirector(stream):
    old_stdout = sys.stdout
    sys.stdout = stream
    try:
        yield
    finally:
        sys.stdout = old_stdout
