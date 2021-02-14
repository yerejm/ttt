#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
test_cli
----------------------------------

Tests for `cli` module.
"""
from unittest.mock import patch

import pytest

from ttt import cli
from ttt.terminal import Terminal


class TestCLI:
    @patch("sys.argv", new=["ttt"])
    def test_no_args(self):
        with patch("ttt.monitor.create_monitor", autospec=True) as monitor:  # noqa
            with pytest.raises(SystemExit):
                cli.run()

    @patch("sys.argv", new=["ttt", "watch_path", "-b", "buildpath", "-g", "Ninja"])
    def test_args(self):
        with patch("ttt.monitor.create_monitor", autospec=True) as monitor:
            cli.run()
            assert len(monitor.call_args_list)
            args, kwargs = monitor.call_args_list[0]
            assert "watch_path" in args
            assert kwargs["build_path"] == "buildpath"
            assert kwargs["generator"] == "Ninja"
            assert kwargs["define"] is None

    @patch("sys.argv", new=["ttt", "watch_path", "-D", "test=y", "-Dfoo=bar"])
    def test_define_list(self):
        with patch("ttt.monitor.create_monitor", autospec=True) as monitor:
            cli.run()
            assert len(monitor.call_args_list)
            args, kwargs = monitor.call_args_list[0]
            assert kwargs["define"] == ["test=y", "foo=bar"]

    @patch("sys.argv", new=["ttt", "watch_path", "-vv"])
    def test_verbosity_multiple(self):
        with patch("ttt.monitor.create_monitor", autospec=True) as monitor:  # noqa
            cli.run()
        assert Terminal.VERBOSITY == 2

    @patch("sys.argv", new=["ttt", "watch_path", "-v"])
    def test_verbosity_single(self):
        with patch("ttt.monitor.create_monitor", autospec=True) as monitor:  # noqa
            cli.run()
        assert Terminal.VERBOSITY == 1

    @patch("sys.argv", new=["ttt", "watch_path"])
    def test_verbosity_none(self):
        with patch("ttt.monitor.create_monitor", autospec=True) as monitor:  # noqa
            cli.run()
        assert Terminal.VERBOSITY == 0

    @patch("sys.argv", new=["ttt", "watch_path", "file1", "file2"])
    def test_patterns(self):
        with patch("ttt.monitor.create_monitor", autospec=True) as monitor:
            cli.run()
            assert len(monitor.call_args_list)
            args, kwargs = monitor.call_args_list[0]
            assert args == ("watch_path", set(["file1", "file2"]))

    @patch("sys.argv", new=["ttt", "watch_path"])
    def test_irc_disabled(self):
        with patch("ttt.monitor.create_monitor", autospec=True) as monitor:
            cli.run()
            assert len(monitor.call_args_list)
            args, kwargs = monitor.call_args_list[0]
            assert kwargs["irc_server"] is None

    @patch("sys.argv", new=["ttt", "watch_path", "-x", "*.o"])
    def test_exclusion(self):
        with patch("ttt.monitor.create_monitor", autospec=True) as monitor:
            cli.run()
            assert len(monitor.call_args_list)
            args, kwargs = monitor.call_args_list[0]
            assert kwargs["exclude"] == ["*.o"]

    @patch("sys.argv", new=["ttt", "watch_path", "-x", "*.o", "-x", "blah"])
    def test_exclusion_list(self):
        with patch("ttt.monitor.create_monitor", autospec=True) as monitor:
            cli.run()
            assert len(monitor.call_args_list)
            args, kwargs = monitor.call_args_list[0]
            assert kwargs["exclude"] == ["*.o", "blah"]

    @patch(
        "sys.argv",
        new=[
            "ttt",
            "watch_path",
            "--irc_server",
            "testserver",
            "--irc_port",
            "6666",
            "--irc_channel",
            "#test",
            "--irc_nick",
            "testtest",
        ],
    )
    def test_irc_enabled(self):
        with patch("ttt.monitor.create_monitor", autospec=True) as monitor:
            cli.run()
            assert len(monitor.call_args_list)
            args, kwargs = monitor.call_args_list[0]
            assert "irc_server" in kwargs
            assert kwargs["irc_server"] == "testserver"
            assert kwargs["irc_port"] == 6666
            assert kwargs["irc_channel"] == "#test"
            assert kwargs["irc_nick"] == "testtest"

    @patch("sys.argv", new=["ttt", "watch_path", "--clean"])
    def test_clean(self):
        with patch("ttt.monitor.create_monitor", autospec=True) as monitor:
            cli.run()
            assert len(monitor.call_args_list)
            args, kwargs = monitor.call_args_list[0]
            assert kwargs["clean"]
