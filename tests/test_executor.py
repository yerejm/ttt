#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
test_executor
----------------------------------

Tests for `executor` module.
"""
import os
import sys

from ttt.executor import CRASHED, Executor, FAILED
from ttt.gtest import GTest


BUILDPATH = os.path.sep + os.path.join("path", "to", "build")
DUMMYPATH = os.path.join(BUILDPATH, "test_core")


class MockTest(GTest):
    def __init__(self, source, executable, term=None):
        super(MockTest, self).__init__(source, executable, term)

    def execute(self, filters):
        pass


def make_test(srcfile, binfile, results):
    g = MockTest(srcfile, binfile)
    for line in results:
        g(sys.stdout, line)
    return g


class TestExecutor:
    def test_passed(self):
        e = Executor()

        g = make_test(
            "test_core.cc",
            DUMMYPATH,
            [
                "[==========] Running 1 test from 1 test case.",
                "[----------] Global test environment set-up.",
                "[----------] 1 test from core",
                "[ RUN      ] core.ok",
                "[       OK ] core.ok (0 ms)",
                "[----------] 1 test from core (1 ms total)",
                "",
                "[----------] Global test environment tear-down",
                "[==========] 1 test from 1 test case ran. (1 ms total)",
                "[  PASSED  ] 1 test.",
            ],
        )
        results = e.test([g])
        assert results == {
            "total_runtime": 0.001,
            "total_passed": 1,
            "total_failed": 0,
            "failures": [],
        }

    def test_failed(self):
        e = Executor()

        g = make_test(
            "test_core.cc",
            DUMMYPATH,
            [
                "[==========] Running 1 test from 1 test case.",
                "[----------] Global test environment set-up.",
                "[----------] 1 test from core",
                "[ RUN      ] core.ok",
                "test_core.cc:12: Failure",
                "Value of: 2",
                "Expected: ok()",
                "Which is: 42",
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
            ],
        )
        results = e.test([g])
        assert results == {
            "total_runtime": 0.001,
            "total_passed": 0,
            "total_failed": 1,
            "failures": [
                [
                    "core.ok",
                    [
                        "test_core.cc:12: Failure",
                        "Value of: 2",
                        "Expected: ok()",
                        "Which is: 42",
                    ],
                    [],
                    FAILED,
                ]
            ],
        }

    def test_windows_seh_crash(self):
        e = Executor()

        g = make_test(
            "test_core.cc",
            DUMMYPATH,
            [
                "[==========] Running 1 test from 1 test case.",
                "[----------] Global test environment set-up.",
                "[----------] 1 test from core",
                "[ RUN      ] core.ok",
                "unknown file: error: SEH exception with code 0xc0000005 thrown in"
                " the test body",
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
            ],
        )
        results = e.test([g])
        assert results == {
            "total_runtime": 0.001,
            "total_passed": 0,
            "total_failed": 1,
            "failures": [
                [
                    "core.ok",
                    [
                        "SEH Exception",
                        "unknown file: error: SEH exception with code "
                        "0xc0000005 thrown in the test body",
                    ],
                    [],
                    CRASHED,
                ]
            ],
        }

    def test_mixed_results(self):
        e = Executor()

        g = make_test(
            "test_core.cc",
            DUMMYPATH,
            [
                "[==========] Running 2 tests from 1 test case.",
                "[----------] Global test environment set-up.",
                "[----------] 2 test from core",
                "[ RUN      ] core.test",
                "[       OK ] core.test (0 ms)",
                "[ RUN      ] core.ok",
                "test_core.cc:12: Failure",
                "Value of: 2",
                "Expected: ok()",
                "Which is: 42",
                "[  FAILED  ] core.ok (0 ms)",
                "[----------] 2 tests from core (1 ms total)",
                "",
                "[----------] Global test environment tear-down",
                "[==========] 2 tests from 1 test case ran. (1 ms total)",
                "[  PASSED  ] 1 test.",
                "[  FAILED  ] 1 test, listed below:",
                "[  FAILED  ] core.ok",
                "",
                " 1 FAILED TEST",
            ],
        )
        results = e.test([g])
        assert results == {
            "total_runtime": 0.001,
            "total_passed": 1,
            "total_failed": 1,
            "failures": [
                [
                    "core.ok",
                    [
                        "test_core.cc:12: Failure",
                        "Value of: 2",
                        "Expected: ok()",
                        "Which is: 42",
                    ],
                    [],
                    FAILED,
                ]
            ],
        }

    def test_filter(self):
        e = Executor()

        g = make_test(
            "test_core.cc",
            DUMMYPATH,
            [
                "[==========] Running 1 test from 1 test case.",
                "[----------] Global test environment set-up.",
                "[----------] 1 test from core",
                "[ RUN      ] core.ok",
                "test_core.cc:12: Failure",
                "Value of: 2",
                "Expected: ok()",
                "Which is: 42",
                "[  FAILED  ] core.ok (0 ms)",
                "[----------] 1 test from core (0 ms total)",
                "",
                "[----------] Global test environment tear-down",
                "[==========] 1 test from 1 test case ran. (0 ms total)",
                "[  PASSED  ] 0 tests.",
                "[  FAILED  ] 1 test, listed below:",
                "[  FAILED  ] core.ok",
                "",
                " 1 FAILED TEST",
            ],
        )
        e.test([g])
        assert e.test_filter() == {DUMMYPATH: ["core.ok"]}
        e.clear_filter()
        assert e.test_filter() == {}

    def test_failed_filter(self):
        e = Executor()

        g = make_test(
            "test_core.cc",
            DUMMYPATH,
            [
                "[==========] Running 2 tests from 1 test case.",
                "[----------] Global test environment set-up.",
                "[----------] 2 test from core",
                "[ RUN      ] core.test",
                "[       OK ] core.test (0 ms)",
                "[ RUN      ] core.ok",
                "test_core.cc:12: Failure",
                "Value of: 2",
                "Expected: ok()",
                "Which is: 42",
                "[  FAILED  ] core.ok (0 ms)",
                "[----------] 2 tests from core (0 ms total)",
                "",
                "[----------] Global test environment tear-down",
                "[==========] 2 tests from 1 test case ran. (0 ms total)",
                "[  PASSED  ] 1 test.",
                "[  FAILED  ] 1 test, listed below:",
                "[  FAILED  ] core.ok",
                "",
                " 1 FAILED TEST",
            ],
        )
        e.test([g])
        assert e.test_filter() == {DUMMYPATH: ["core.ok"]}

        g = make_test(
            "test_core.cc",
            DUMMYPATH,
            [
                "[==========] Running 1 test from 1 test case.",
                "[----------] Global test environment set-up.",
                "[----------] 1 test from core",
                "[ RUN      ] core.ok",
                "test_core.cc:12: Failure",
                "Value of: 2",
                "Expected: ok()",
                "Which is: 42",
                "[  FAILED  ] core.ok (0 ms)",
                "[----------] 1 test from core (0 ms total)",
                "",
                "[----------] Global test environment tear-down",
                "[==========] 1 test from 1 test case ran. (0 ms total)",
                "[  PASSED  ] 0 tests.",
                "[  FAILED  ] 1 test, listed below:",
                "[  FAILED  ] core.ok",
                "",
                " 1 FAILED TEST",
            ],
        )
        e.test([g])
        assert e.test_filter() == {DUMMYPATH: ["core.ok"]}

    def test_multiple_failed_filter(self):
        e = Executor()

        g = make_test(
            "test_core.cc",
            DUMMYPATH,
            [
                "[==========] Running 2 tests from 1 test case.",
                "[----------] Global test environment set-up.",
                "[----------] 2 test from core",
                "[ RUN      ] core.test",
                "test_core.cc:12: Failure",
                "Value of: 2",
                "Expected: ok()",
                "Which is: 42",
                "[  FAILED  ] core.test (0 ms)",
                "[ RUN      ] core.ok",
                "test_core.cc:12: Failure",
                "Value of: 2",
                "Expected: ok()",
                "Which is: 42",
                "[  FAILED  ] core.ok (0 ms)",
                "[----------] 2 tests from core (0 ms total)",
                "",
                "[----------] Global test environment tear-down",
                "[==========] 2 tests from 1 test case ran. (0 ms total)",
                "[  PASSED  ] 0 tests.",
                "[  FAILED  ] 2 test, listed below:",
                "[  FAILED  ] core.test",
                "[  FAILED  ] core.ok",
                "",
                " 2 FAILED TESTS",
            ],
        )
        e.test([g])
        assert e.test_filter() == {DUMMYPATH: ["core.test", "core.ok"]}

        g = make_test(
            "test_core.cc",
            DUMMYPATH,
            [
                "[==========] Running 2 tests from 1 test case.",
                "[----------] Global test environment set-up.",
                "[----------] 2 test from core",
                "[ RUN      ] core.test",
                "test_core.cc:12: Failure",
                "Value of: 2",
                "Expected: ok()",
                "Which is: 42",
                "[  FAILED  ] core.test (0 ms)",
                "[ RUN      ] core.ok",
                "test_core.cc:12: Failure",
                "Value of: 2",
                "Expected: ok()",
                "Which is: 42",
                "[  FAILED  ] core.ok (0 ms)",
                "[----------] 2 tests from core (0 ms total)",
                "",
                "[----------] Global test environment tear-down",
                "[==========] 2 tests from 1 test case ran. (0 ms total)",
                "[  PASSED  ] 0 tests.",
                "[  FAILED  ] 2 test, listed below:",
                "[  FAILED  ] core.test",
                "[  FAILED  ] core.ok",
                "",
                " 2 FAILED TESTS",
            ],
        )
        e.test([g])
        assert e.test_filter() == {DUMMYPATH: ["core.test", "core.ok"]}

    def test_failure_then_success_reruns_all(self):
        e = Executor()

        g = make_test(
            "test_core.cc",
            DUMMYPATH,
            [
                "[==========] Running 1 test from 1 test case.",
                "[----------] Global test environment set-up.",
                "[----------] 1 test from core",
                "[ RUN      ] core.ok",
                "test_core.cc:12: Failure",
                "Value of: 2",
                "Expected: ok()",
                "Which is: 42",
                "[  FAILED  ] core.ok (0 ms)",
                "[----------] 1 test from core (0 ms total)",
                "",
                "[----------] Global test environment tear-down",
                "[==========] 1 test from 1 test case ran. (0 ms total)",
                "[  PASSED  ] 0 tests.",
                "[  FAILED  ] 1 test, listed below:",
                "[  FAILED  ] core.ok",
                "",
                " 1 FAILED TEST",
            ],
        )
        e.test([g])
        assert e.test_filter() == {DUMMYPATH: ["core.ok"]}

        g = make_test(
            "test_core.cc",
            DUMMYPATH,
            [
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
            ],
        )
        e.test([g])
        assert e.test_filter() == {}
