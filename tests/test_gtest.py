#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
test_gtest
----------------------------------

Tests for `gtest` module.
"""
import io
import os
import sys
from unittest.mock import patch

import pytest

from ttt.executor import CRASHED
from ttt.gtest import GTest, GTestException
from ttt.terminal import Terminal


class TestGTest:
    def test_run_time(self):
        results = [
            "Running main() from gtest_main.cc",
            "[==========] Running 2 tests from 1 test case.",
            "[----------] Global test environment set-up.",
            "[----------] 2 tests from dummy",
            "[ RUN      ] dummy.test1",
            "[       OK ] dummy.test1 (0 ms)",
            "[ RUN      ] dummy.test2",
            "[       OK ] dummy.test2 (0 ms)",
            "[----------] 2 tests from dummy (0 ms total)",
            "",
            "[----------] Global test environment tear-down",
            "[==========] 2 tests from 1 test case ran. (3 ms total)",
            "[  PASSED  ] 2 tests.",
        ]
        f = io.StringIO()
        gtest = GTest("/test/test_core.cc", "test_core", term=Terminal(f))
        for line in results:
            gtest(sys.stdout, line)

        assert gtest.run_time() == 3

    def test_one_testcase_one_success(self):
        results = [
            "Running main() from gtest_main.cc",
            "Note: Google Test filter = core.ok",
            "[==========] Running 1 test from 1 test case.",
            "[----------] Global test environment set-up.",
            "[----------] 1 test from core",
            "[ RUN      ] core.ok",
            "[       OK ] core.ok (0 ms)",
            "[----------] 1 test from core (0 ms total)",
            "",
            "[----------] Global test environment tear-down",
            "[==========] 1 test from 1 test case ran. (0 ms total)",
            "[  PASSED  ] 1 test.",
        ]
        f = io.StringIO()
        gtest = GTest("/test/test_core.cc", "test_core", term=Terminal(f))
        for line in results:
            gtest(sys.stdout, line)

        assert f.getvalue() == "/test/test_core.cc :: core ." + os.linesep
        assert gtest.results() == {"core.ok": (False, [], [])}
        assert gtest.failures() == []
        assert gtest.fails() == 0
        assert gtest.passes() == 1

    def test_one_testcase_success(self):
        results = [
            "Running main() from gtest_main.cc",
            "[==========] Running 2 tests from 1 test case.",
            "[----------] Global test environment set-up.",
            "[----------] 2 tests from dummy",
            "[ RUN      ] dummy.test1",
            "[       OK ] dummy.test1 (0 ms)",
            "[ RUN      ] dummy.test2",
            "[       OK ] dummy.test2 (0 ms)",
            "[----------] 2 tests from dummy (0 ms total)",
            "",
            "[----------] Global test environment tear-down",
            "[==========] 2 tests from 1 test case ran. (0 ms total)",
            "[  passed  ] 2 tests.",
        ]
        f = io.StringIO()
        gtest = GTest("/test/test_core.cc", "test_core", term=Terminal(f))
        for line in results:
            gtest(sys.stdout, line)

        assert f.getvalue() == "/test/test_core.cc :: dummy .." + os.linesep
        assert gtest.results() == {
            "dummy.test1": (False, [], []),
            "dummy.test2": (False, [], []),
        }
        assert gtest.failures() == []
        assert gtest.fails() == 0
        assert gtest.passes() == 2

    def test_multiple_testcase_success(self):
        results = [
            "Running main() from gtest_main.cc",
            "[==========] Running 6 tests from 2 test cases.",
            "[----------] Global test environment set-up.",
            "[----------] 4 tests from core",
            "[ RUN      ] core.ok",
            "[       OK ] core.ok (0 ms)",
            "[ RUN      ] core.okshadow",
            "[       OK ] core.okshadow (0 ms)",
            "[ RUN      ] core.notok",
            "[       OK ] core.notok (0 ms)",
            "[ RUN      ] core.blah",
            "[       OK ] core.blah (0 ms)",
            "[----------] 4 tests from core (0 ms total)",
            "",
            "[----------] 2 tests from blah",
            "[ RUN      ] blah.test1",
            "[       OK ] blah.test1 (0 ms)",
            "[ RUN      ] blah.test2",
            "[       OK ] blah.test2 (0 ms)",
            "[----------] 2 tests from blah (0 ms total)",
            "",
            "[----------] Global test environment tear-down",
            "[==========] 6 tests from 2 test cases ran. (0 ms total)",
            "[  PASSED  ] 6 tests.",
        ]
        f = io.StringIO()
        gtest = GTest("/test/test_core.cc", "test_core", term=Terminal(f))
        for line in results:
            gtest(sys.stdout, line)

        assert (
            f.getvalue()
            == os.linesep.join(
                ["/test/test_core.cc :: core ....", "/test/test_core.cc :: blah .."]
            )
            + os.linesep
        )
        assert gtest.results() == {
            "core.ok": (False, [], []),
            "core.okshadow": (False, [], []),
            "core.notok": (False, [], []),
            "core.blah": (False, [], []),
            "blah.test1": (False, [], []),
            "blah.test2": (False, [], []),
        }
        assert gtest.failures() == []
        assert gtest.fails() == 0
        assert gtest.passes() == 6

    def test_one_testcase_failure(self):
        results = [
            "Running main() from gtest_main.cc",
            "Note: Google Test filter = core.ok:core.ok:core.okshadow",
            "[==========] Running 2 tests from 1 test case.",
            "[----------] Global test environment set-up.",
            "[----------] 2 tests from core",
            "[ RUN      ] core.ok",
            "/test/test_core.cc:12: Failure",
            "Value of: 2",
            "Expected: ok()",
            "Which is: 42",
            "[  FAILED  ] core.ok (0 ms)",
            "[ RUN      ] core.okshadow",
            "/test/test_core.cc:16: Failure",
            "Value of: 1",
            "Expected: ok()",
            "Which is: 42",
            "[  FAILED  ] core.okshadow (0 ms)",
            "[----------] 2 tests from core (0 ms total)",
            "",
            "[----------] Global test environment tear-down",
            "[==========] 2 tests from 1 test case ran. (0 ms total)",
            "[  PASSED  ] 0 tests.",
            "[  FAILED  ] 2 tests, listed below:",
            "[  FAILED  ] core.ok",
            "[  FAILED  ] core.okshadow",
            "",
            " 2 FAILED TESTS",
        ]
        f = io.StringIO()
        gtest = GTest("/test/test_core.cc", "test_core", term=Terminal(f))
        for line in results:
            gtest(sys.stdout, line)

        assert f.getvalue() == "/test/test_core.cc :: core FF" + os.linesep
        assert gtest.results() == {
            "core.ok": (
                True,
                [
                    "/test/test_core.cc:12: Failure",
                    "Value of: 2",
                    "Expected: ok()",
                    "Which is: 42",
                ],
                [],
            ),
            "core.okshadow": (
                True,
                [
                    "/test/test_core.cc:16: Failure",
                    "Value of: 1",
                    "Expected: ok()",
                    "Which is: 42",
                ],
                [],
            ),
        }
        assert gtest.failures() == ["core.ok", "core.okshadow"]
        assert gtest.fails() == 2
        assert gtest.passes() == 0

    def test_multiple_testcase_failure(self):
        results = (
            0,
            [
                "Running main() from gtest_main.cc",
                "[==========] Running 6 tests from 2 test cases.",
                "[----------] Global test environment set-up.",
                "[----------] 4 tests from core",
                "[ RUN      ] core.ok",
                "[       OK ] core.ok (0 ms)",
                "[ RUN      ] core.okshadow",
                "/test/test_core.cc:16: Failure",
                "Value of: 2",
                "Expected: ok()",
                "Which is: 42",
                "[  FAILED  ] core.okshadow (0 ms)",
                "[ RUN      ] core.notok",
                "[       OK ] core.notok (0 ms)",
                "[ RUN      ] core.blah",
                "[       OK ] core.blah (0 ms)",
                "[----------] 4 tests from core (0 ms total)",
                "",
                "[----------] 2 tests from blah",
                "[ RUN      ] blah.test1",
                "[       OK ] blah.test1 (0 ms)",
                "[ RUN      ] blah.test2",
                "/test/test_core.cc:32: Failure",
                "Value of: false",
                "  Actual: false",
                "Expected: true",
                "[  FAILED  ] blah.test2 (0 ms)",
                "[----------] 2 tests from blah (0 ms total)",
                "",
                "[----------] Global test environment tear-down",
                "[==========] 6 tests from 2 test cases ran. (1 ms total)",
                "[  PASSED  ] 4 tests.",
                "[  FAILED  ] 2 tests, listed below:",
                "[  FAILED  ] core.okshadow",
                "[  FAILED  ] blah.test2",
            ],
            [],
        )

        f = io.StringIO()
        gtest = GTest("/test/test_core.cc", "test_core", term=Terminal(f))
        for line in results[1]:
            gtest(sys.stdout, line)

        assert (
            f.getvalue()
            == os.linesep.join(
                ["/test/test_core.cc :: core .F..", "/test/test_core.cc :: blah .F"]
            )
            + os.linesep
        )
        assert gtest.results() == {
            "core.ok": (False, [], []),
            "core.okshadow": (
                True,
                [
                    "/test/test_core.cc:16: Failure",
                    "Value of: 2",
                    "Expected: ok()",
                    "Which is: 42",
                ],
                [],
            ),
            "core.notok": (False, [], []),
            "core.blah": (False, [], []),
            "blah.test1": (False, [], []),
            "blah.test2": (
                True,
                [
                    "/test/test_core.cc:32: Failure",
                    "Value of: false",
                    "  Actual: false",
                    "Expected: true",
                ],
                [],
            ),
        }
        assert gtest.failures() == ["core.okshadow", "blah.test2"]
        assert gtest.fails() == 2
        assert gtest.passes() == 4

    def test_windows_seh_crash_failure(self):
        results = [
            "Running main() from gtest_main.cc",
            "[==========] Running 2 tests from 1 test case.",
            "[----------] Global test environment set-up.",
            "[----------] 2 tests from core",
            "[ RUN      ] core.ok",
            "unknown file: error: SEH exception with code 0xc0000005 thrown in the test body",  # noqa
            "[  FAILED  ] core.ok (0 ms)",
            "[----------] 1 test from core (1 ms total)",
            "",
            "[----------] Global test environment tear-down",
            "[==========] 1 test from 1 test case ran. (1 ms total)",
            "[  PASSED  ] 0 tests.",
            "[  FAILED  ] 1 test, listed below:",
            "[  FAILED  ] core.ok",
            "",
            " 1 FAILED TEST",
        ]
        f = io.StringIO()
        gtest = GTest("/test/test_core.cc", "test_core", term=Terminal(f))
        for line in results:
            gtest(sys.stdout, line)

        assert f.getvalue() == "/test/test_core.cc :: core X" + os.linesep
        assert gtest.results() == {
            "core.ok": (
                CRASHED,
                [
                    "SEH Exception",
                    "unknown file: error: SEH exception with code 0xc0000005 thrown in the test body",  # noqa
                ],
                [],
            ),
        }
        assert gtest.failures() == ["core.ok"]
        assert gtest.fails() == 1
        assert gtest.passes() == 0

    def test_command_filter_none(self):
        r = (0, [], [])
        gtest = GTest("/test/test_core.cc", "/path/to/test")
        with patch("ttt.subproc.streamed_call", return_value=r) as c:
            gtest.execute([])
        args = c.call_args[0]
        assert args[0] == ["/path/to/test"]

    def test_command_filter_one(self):
        r = (0, [], [])
        gtest = GTest("/test/test_core.cc", "/path/to/test")
        with patch("ttt.subproc.streamed_call", return_value=r) as c:
            gtest.execute(["dummy"])
        args = c.call_args[0]
        assert args[0] == ["/path/to/test", "--gtest_filter=dummy"]

    def test_command_filter_many(self):
        r = (0, [], [])
        gtest = GTest("/test/test_core.cc", "/path/to/test")
        with patch("ttt.subproc.streamed_call", return_value=r) as c:
            gtest.execute(["dummy1", "dummy2"])
        args = c.call_args[0]
        assert args[0] == ["/path/to/test", "--gtest_filter=dummy1:dummy2"]

    def test_corrupt_test_output_missing_testcase(self):
        f = io.StringIO()
        gtest = GTest("/test/test_core.cc", "test_core", term=Terminal(f))

        with pytest.raises(GTestException):
            gtest.end_test("")

        gtest._testcase = ""

        with pytest.raises(GTestException):
            gtest.end_test("")

        gtest._test = ""

        gtest.end_test("")

        assert f.getvalue() == "."

    def test_detailed_verbosity(self):
        results = [
            "Running main() from gtest_main.cc",
            "Note: Google Test filter = core.ok",
            "[==========] Running 1 test from 1 test case.",
            "[----------] Global test environment set-up.",
            "[----------] 1 test from core",
            "[ RUN      ] core.ok",
            "[       OK ] core.ok (0 ms)",
            "[----------] 1 test from core (0 ms total)",
            "",
            "[----------] Global test environment tear-down",
            "[==========] 1 test from 1 test case ran. (0 ms total)",
            "[  PASSED  ] 1 test.",
        ]
        f = io.StringIO()
        gtest = GTest("/test/test_core.cc", "test_core", term=Terminal(f, verbosity=1))
        for line in results:
            gtest(sys.stdout, line)

        import termstyle

        expected_results = results[:2]
        for line in results[2:]:
            if line.startswith("["):
                expected_results.append(
                    "{}{}".format(
                        termstyle.green(termstyle.bold(line[:13])),
                        line[13:],
                    )
                )
            else:
                expected_results.append(line)
        assert f.getvalue() == os.linesep.join(expected_results) + os.linesep

    def test_detailed_raw_verbosity(self):
        results = [
            "Running main() from gtest_main.cc",
            "Note: Google Test filter = core.ok",
            "[==========] Running 1 test from 1 test case.",
            "[----------] Global test environment set-up.",
            "[----------] 1 test from core",
            "[ RUN      ] core.ok",
            "[       OK ] core.ok (0 ms)",
            "[----------] 1 test from core (0 ms total)",
            "",
            "[----------] Global test environment tear-down",
            "[==========] 1 test from 1 test case ran. (0 ms total)",
            "[  PASSED  ] 1 test.",
        ]
        f = io.StringIO()
        gtest = GTest("/test/test_core.cc", "test_core", term=Terminal(f, verbosity=2))
        r = (0, results, [])
        with patch("ttt.subproc.streamed_call", return_value=r) as c:  # noqa
            gtest.execute([])

        header = ["Executing test_core", "['test_core']"]
        assert f.getvalue() == (
            os.linesep.join(header) + os.linesep + os.linesep.join(results) + os.linesep
        )
