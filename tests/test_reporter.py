#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
test_reporter
----------------------------------

Tests for `reporter` module.
"""
import io
import os

from ttt import __progname__, __version__
from ttt.executor import FAILED
from ttt.terminal import Terminal, TerminalReporter
import ttt.termstyle as termstyle
from ttt.watcher import WatchState


class TestReporter:
    def test_session_start(self):
        f = io.StringIO()
        r = TerminalReporter(
            watch_path=None, build_path=None, terminal=Terminal(stream=f)
        )

        r.session_start("test")
        assert f.getvalue() == (
            termstyle.bold(
                "".ljust(28, "=") + " test session starts " + "".ljust(29, "=")
            )
            + os.linesep
        )

    def test_wait_change(self):
        f = io.StringIO()
        r = TerminalReporter(
            watch_path="watch_path",
            build_path="build_path",
            terminal=Terminal(stream=f),
            timestamp=lambda: "timestamp",
        )

        r.wait_change()
        assert (
            f.getvalue()
            == termstyle.bold(
                "".ljust(28, "#") + " waiting for changes " + "".ljust(29, "#")
            )
            + os.linesep
            + termstyle.bold("### Since:      timestamp")
            + os.linesep
            + termstyle.bold("### Watching:   watch_path")
            + os.linesep
            + termstyle.bold("### Build at:   build_path")
            + os.linesep
            + termstyle.bold("### Using {}:  {}".format(__progname__, __version__))
            + os.linesep
        )

    def test_report_all_passed(self):
        f = io.StringIO()
        r = TerminalReporter(
            watch_path=None, build_path=None, terminal=Terminal(stream=f)
        )

        results = {
            "total_runtime": 2.09,
            "total_passed": 1,
            "total_failed": 0,
            "failures": [],
        }
        r.report_results(results)
        assert f.getvalue() == (
            termstyle.bold(
                termstyle.green(
                    "".ljust(26, "=") + " 1 passed in 2.09 seconds " + "".ljust(26, "=")
                )
            )
            + os.linesep
        )

    def test_report_all_failed(self):
        f = io.StringIO()
        r = TerminalReporter(
            watch_path="/path", build_path=None, terminal=Terminal(stream=f)
        )

        results = {
            "total_runtime": 2.09,
            "total_passed": 0,
            "total_failed": 1,
            "failures": [
                [
                    "fail1",
                    [
                        "/path/to/file:12: blah",
                        "results line 2",
                        "results line 3",
                        "results line 4",
                    ],
                    [],
                    FAILED,
                ],
            ],
        }
        r.report_results(results)
        expected = [
            "================================== FAILURES ==================================",  # noqa
            termstyle.bold(
                termstyle.red(
                    "___________________________________ fail1 ____________________________________"  # noqa
                )
            ),
            "/path/to/file:12: blah",
            "results line 2",
            "results line 3",
            "results line 4",
            termstyle.bold(
                termstyle.red(
                    "_________________________________ to/file:12 _________________________________"  # noqa
                )
            ),
            termstyle.bold(
                termstyle.red(
                    "===================== 1 failed, 0 passed in 2.09 seconds ====================="  # noqa
                )
            ),
        ]
        actual = f.getvalue().splitlines()
        assert actual == expected

    def test_report_multiple_failed(self):
        f = io.StringIO()
        r = TerminalReporter(
            watch_path="/path", build_path=None, terminal=Terminal(stream=f)
        )

        results = {
            "total_runtime": 2.09,
            "total_passed": 0,
            "total_failed": 2,
            "failures": [
                [
                    "fail1",
                    [
                        "/path/to/file:12: blah",
                        "results line 2",
                        "results line 3",
                        "results line 4",
                    ],
                    [],
                    FAILED,
                ],
                [
                    "fail2",
                    [
                        "/path/to/file:102: blah",
                        "results line 2",
                        "results line 3",
                        "results line 4",
                    ],
                    [],
                    FAILED,
                ],
            ],
        }
        r.report_results(results)
        expected = [
            "================================== FAILURES ==================================",  # noqa
            termstyle.bold(
                termstyle.red(
                    "___________________________________ fail1 ____________________________________"  # noqa
                )
            ),
            "/path/to/file:12: blah",
            "results line 2",
            "results line 3",
            "results line 4",
            termstyle.bold(
                termstyle.red(
                    "_________________________________ to/file:12 _________________________________"  # noqa
                )
            ),
            termstyle.bold(
                termstyle.red(
                    "___________________________________ fail2 ____________________________________"  # noqa
                )
            ),
            "/path/to/file:102: blah",
            "results line 2",
            "results line 3",
            "results line 4",
            termstyle.bold(
                termstyle.red(
                    "________________________________ to/file:102 _________________________________"  # noqa
                )
            ),
            termstyle.bold(
                termstyle.red(
                    "===================== 2 failed, 0 passed in 2.09 seconds ====================="  # noqa
                )
            ),
        ]
        actual = f.getvalue().splitlines()
        assert actual == expected

    def test_report_watchstate(self):
        f = io.StringIO()
        r = TerminalReporter(
            watch_path=None, build_path=None, terminal=Terminal(stream=f)
        )

        r.report_watchstate(WatchState(["create"], ["delete"], ["modify"], 1.0))
        assert (
            f.getvalue()
            == os.linesep.join(
                [
                    termstyle.green("# CREATED create"),
                    termstyle.yellow("# MODIFIED modify"),
                    termstyle.red("# DELETED delete"),
                    "### Scan time:      1.000s",
                ]
            )
            + os.linesep
        )

    def test_interrupt_detected(self):
        f = io.StringIO()
        r = TerminalReporter(
            watch_path=None, build_path=None, terminal=Terminal(stream=f)
        )

        r.interrupt_detected()
        assert f.getvalue() == (os.linesep + "Interrupt again to exit." + os.linesep)

    def test_halt(self):
        f = io.StringIO()
        r = TerminalReporter(
            watch_path=None, build_path=None, terminal=Terminal(stream=f)
        )

        r.halt()
        assert f.getvalue() == os.linesep + "Watching stopped." + os.linesep

    def test_report_build_path(self):
        f = io.StringIO()
        r = TerminalReporter(
            watch_path="watch_path",
            build_path="build_path",
            terminal=Terminal(stream=f),
        )

        r.report_build_path()
        assert f.getvalue() == (
            termstyle.bold("### Building:   build_path") + os.linesep
        )

    def test_report_interrupt(self):
        f = io.StringIO()
        r = TerminalReporter(
            watch_path="watch_path",
            build_path="build_path",
            terminal=Terminal(stream=f),
        )

        try:
            raise KeyboardInterrupt()
        except KeyboardInterrupt as e:
            r.report_interrupt(e)

        assert f.getvalue() == (
            "".ljust(29, "!") + " KeyboardInterrupt " + "".ljust(30, "!") + os.linesep
        )

    def test_report_with_stdout_and_stderr_in_additional_output(self):
        f = io.StringIO()
        r = TerminalReporter(
            watch_path="/path", build_path=None, terminal=Terminal(stream=f)
        )

        results = {
            "total_runtime": 2.09,
            "total_passed": 0,
            "total_failed": 1,
            "failures": [
                [
                    "fail1",
                    [
                        "extra line 1",
                        "extra line 2",
                        "/path/to/file:12: blah",
                        "results line 1",
                        "results line 2",
                        "results line 3",
                    ],
                    [],
                    FAILED,
                ],
            ],
        }
        r.report_results(results)
        expected = [
            "================================== FAILURES ==================================",  # noqa
            termstyle.bold(
                termstyle.red(
                    "___________________________________ fail1 ____________________________________"  # noqa
                )
            ),
            "/path/to/file:12: blah",
            "results line 1",
            "results line 2",
            "results line 3",
            "----------------------------- Additional output ------------------------------",  # noqa
            "extra line 1",
            "extra line 2",
            termstyle.bold(
                termstyle.red(
                    "_________________________________ to/file:12 _________________________________"  # noqa
                )
            ),
            termstyle.bold(
                termstyle.red(
                    "===================== 1 failed, 0 passed in 2.09 seconds ====================="  # noqa
                )
            ),
        ]
        actual = f.getvalue().splitlines()
        assert actual == expected

    def test_path_stripping_in_test_failure_last_line(self):
        f = io.StringIO()
        r = TerminalReporter(
            watch_path="/path/to/watch",
            build_path="/path/to/build",
            terminal=Terminal(stream=f),
        )

        failures = [
            [
                "core.ok",
                [
                    "/path/to/watch/test/test_core.cc:12: Failure",
                    "Value of: 2",
                    "Expected: ok()",
                    "Which is: 42",
                ],
                [],
                FAILED,
            ]
        ]
        r.report_failures(failures)
        expected = [
            "================================== FAILURES ==================================",  # noqa
            termstyle.bold(
                termstyle.red(
                    "__________________________________ core.ok ___________________________________"  # noqa
                )
            ),
            "/path/to/watch/test/test_core.cc:12: Failure",
            "Value of: 2",
            "Expected: ok()",
            "Which is: 42",
            termstyle.bold(
                termstyle.red(
                    "____________________________ test/test_core.cc:12 ____________________________",  # noqa
                )
            ),
        ]
        actual = f.getvalue().splitlines()
        assert actual == expected
