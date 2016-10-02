#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
test_cli
----------------------------------

Tests for `cli` module.
"""
import pytest
try:
    from mock import Mock, MagicMock, call, patch
except:
    from unittest.mock import Mock, MagicMock, call, patch

from ttt import monitor
from ttt import cli
from ttt.terminal import Terminal


class TestCLI:
    @patch('sys.argv', new=['ttt'])
    def test_no_args(self):
        with patch('ttt.monitor.create_monitor', autospec=True) as monitor:
            with pytest.raises(SystemExit):
                cli.run()

    @patch('sys.argv', new=['ttt', 'watch_path', '-b', 'buildpath', '-g', 'Ninja'])
    def test_args(self):
        with patch('ttt.monitor.create_monitor', autospec=True) as monitor:
            cli.run()
            assert len(monitor.call_args_list)
            args, kwargs = monitor.call_args_list[0]
            assert 'watch_path' in args
            assert kwargs['build_path'] == 'buildpath'
            assert kwargs['generator'] == 'Ninja'
            assert kwargs['define'] == None

    @patch('sys.argv', new=['ttt', 'watch_path', '-D', 'test=yes', '-Dfoo=bar'])
    def test_define_list(self):
        with patch('ttt.monitor.create_monitor', autospec=True) as monitor:
            cli.run()
            assert len(monitor.call_args_list)
            args, kwargs = monitor.call_args_list[0]
            assert kwargs['define'] == ['test=yes', 'foo=bar']

    @patch('sys.argv', new=['ttt', 'watch_path', '-vv'])
    def test_verbosity_multiple(self):
        with patch('ttt.monitor.create_monitor', autospec=True) as monitor:
            cli.run()
        assert Terminal.VERBOSITY == 2

    @patch('sys.argv', new=['ttt', 'watch_path', '-v'])
    def test_verbosity_single(self):
        with patch('ttt.monitor.create_monitor', autospec=True) as monitor:
            cli.run()
        assert Terminal.VERBOSITY == 1

    @patch('sys.argv', new=['ttt', 'watch_path'])
    def test_verbosity_none(self):
        with patch('ttt.monitor.create_monitor', autospec=True) as monitor:
            cli.run()
        assert Terminal.VERBOSITY == 0

    @patch('sys.argv', new=['ttt', 'watch_path', 'file1', 'file2'])
    def test_patterns(self):
        with patch('ttt.monitor.create_monitor', autospec=True) as monitor:
            cli.run()
            assert len(monitor.call_args_list)
            args, kwargs = monitor.call_args_list[0]
            assert args == ('watch_path', set(['file1', 'file2']))

    @patch('sys.argv', new=['ttt', 'watch_path'])
    def test_irc_disabled(self):
        with patch('ttt.monitor.create_monitor', autospec=True) as monitor:
            cli.run()
            assert len(monitor.call_args_list)
            args, kwargs = monitor.call_args_list[0]
            assert kwargs['irc_server'] is None

    @patch('sys.argv', new=['ttt', 'watch_path',
        '--irc_server', 'testserver', '--irc_port', '6666',
        '--irc_channel', '#test', '--irc_nick', 'testtest'])
    def test_irc_enabled(self):
        with patch('ttt.monitor.create_monitor', autospec=True) as monitor:
            cli.run()
            assert len(monitor.call_args_list)
            args, kwargs = monitor.call_args_list[0]
            assert 'irc_server' in kwargs
            assert kwargs['irc_server'] == 'testserver'
            assert kwargs['irc_port'] == 6666
            assert kwargs['irc_channel'] == '#test'
            assert kwargs['irc_nick'] == 'testtest'
