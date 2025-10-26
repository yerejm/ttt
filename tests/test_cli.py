#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
test_cli
----------------------------------

Tests for `cli` module.
"""
from unittest.mock import patch

from click.testing import CliRunner

from ttt.cli import ttt
from ttt.terminal import Terminal


class TestCLI:
    def test_no_args(self):
        runner = CliRunner()
        result = runner.invoke(ttt)
        assert result.exit_code == 2
        assert "ttt [OPTIONS] WATCH_PATH [FILENAME]..." in result.output
        assert "Error: Missing argument 'WATCH_PATH'." in result.output

    def test_args(self):
        with patch("ttt.monitor.create_monitor", autospec=True) as monitor:
            runner = CliRunner()
            result = runner.invoke(
                ttt, ["watch_path", "--build-path", "buildpath", "--generator", "Ninja"]
            )
            assert result.exit_code == 0
            assert len(monitor.call_args_list)
            args, kwargs = monitor.call_args_list[0]
            assert kwargs["watch_path"] == "watch_path"
            assert kwargs["build_path"] == "buildpath"
            assert kwargs["generator"] == "Ninja"
            assert kwargs["define"] == ()

    def test_define_list(self):
        with patch("ttt.monitor.create_monitor", autospec=True) as monitor:
            runner = CliRunner()
            result = runner.invoke(ttt, ["watch_path", "-D", "test=y", "-Dfoo=bar"])
            assert result.exit_code == 0
            assert len(monitor.call_args_list)
            args, kwargs = monitor.call_args_list[0]
            assert kwargs["define"] == ("test=y", "foo=bar")

    def test_verbosity_multiple(self):
        with patch("ttt.monitor.create_monitor", autospec=True) as monitor:  # noqa
            runner = CliRunner()
            result = runner.invoke(ttt, ["watch_path", "-vv"])
            assert result.exit_code == 0
        assert Terminal.VERBOSITY == 2

    def test_verbosity_single(self):
        with patch("ttt.monitor.create_monitor", autospec=True) as monitor:  # noqa
            runner = CliRunner()
            result = runner.invoke(ttt, ["watch_path", "-v"])
            assert result.exit_code == 0
        assert Terminal.VERBOSITY == 1

    def test_verbosity_none(self):
        with patch("ttt.monitor.create_monitor", autospec=True) as monitor:  # noqa
            runner = CliRunner()
            result = runner.invoke(ttt, ["watch_path"])
            assert result.exit_code == 0
        assert Terminal.VERBOSITY == 0

    def test_patterns(self):
        with patch("ttt.monitor.create_monitor", autospec=True) as monitor:
            runner = CliRunner()
            result = runner.invoke(ttt, ["watch_path", "file1", "file2"])
            assert result.exit_code == 0
            assert len(monitor.call_args_list)
            args, kwargs = monitor.call_args_list[0]
            assert kwargs["patterns"] == set(["file1", "file2"])

    def test_exclusion(self):
        with patch("ttt.monitor.create_monitor", autospec=True) as monitor:
            runner = CliRunner()
            result = runner.invoke(ttt, ["watch_path", "--exclude", "*.o"])
            assert result.exit_code == 0
            assert len(monitor.call_args_list)
            args, kwargs = monitor.call_args_list[0]
            assert kwargs["exclude"] == ("*.o",)

    def test_exclusion_list(self):
        with patch("ttt.monitor.create_monitor", autospec=True) as monitor:
            runner = CliRunner()
            result = runner.invoke(
                ttt, ["watch_path", "--exclude", "*.o", "--exclude", "blah"]
            )
            assert result.exit_code == 0
            assert len(monitor.call_args_list)
            args, kwargs = monitor.call_args_list[0]
            assert kwargs["exclude"] == ("*.o", "blah")

    def test_clean(self):
        with patch("ttt.monitor.create_monitor", autospec=True) as monitor:
            runner = CliRunner()
            result = runner.invoke(ttt, ["watch_path", "-c"])
            assert result.exit_code == 0
            assert len(monitor.call_args_list)
            args, kwargs = monitor.call_args_list[0]
            assert kwargs["clean"]
