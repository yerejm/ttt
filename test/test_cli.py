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

from ttt import systemcontext
from ttt import monitor
from ttt import cli


class TestCLI:
    @patch('sys.argv', new=['ttt'])
    def test_no_args(self):
        with patch('ttt.systemcontext.create_context', autospec=True) as context:
            with patch('ttt.monitor.create_monitor', autospec=True) as monitor:
                with pytest.raises(SystemExit):
                    cli.run()

    @patch('sys.argv', new=['ttt', 'watch_path', '-b', 'buildpath', '-g', 'Ninja'])
    def test_args(self):
        context = MagicMock()
        with patch('ttt.systemcontext.create_context', return_value=context):
            with patch('ttt.monitor.create_monitor', autospec=True) as monitor:
                cli.run()
                assert len(monitor.call_args_list)
                args, kwargs = monitor.call_args_list[0]
                assert 'watch_path' in args
                assert kwargs['build_path'] == 'buildpath'
                assert kwargs['generator'] == 'Ninja'

    @patch('sys.argv', new=['ttt', 'watch_path', '-vv'])
    def test_verbosity_multiple(self):
        context = MagicMock()
        with patch('ttt.systemcontext.create_context', return_value=context):
            with patch('ttt.monitor.create_monitor', autospec=True) as monitor:
                cli.run()
                assert len(monitor.call_args_list)
                args, kwargs = monitor.call_args_list[0]
                assert kwargs['verbosity'] == 2

    @patch('sys.argv', new=['ttt', 'watch_path', '-v'])
    def test_verbosity_single(self):
        context = MagicMock()
        with patch('ttt.systemcontext.create_context', return_value=context):
            with patch('ttt.monitor.create_monitor', autospec=True) as monitor:
                cli.run()
                assert len(monitor.call_args_list)
                args, kwargs = monitor.call_args_list[0]
                assert kwargs['verbosity'] == 1

    @patch('sys.argv', new=['ttt', 'watch_path'])
    def test_verbosity_none(self):
        context = MagicMock()
        with patch('ttt.systemcontext.create_context', return_value=context):
            with patch('ttt.monitor.create_monitor', autospec=True) as monitor:
                cli.run()
                assert len(monitor.call_args_list)
                args, kwargs = monitor.call_args_list[0]
                assert kwargs['verbosity'] is None

    @patch('sys.argv', new=['ttt', 'watch_path'])
    def test_irc_disabled(self):
        context = MagicMock()
        with patch('ttt.systemcontext.create_context', return_value=context):
            with patch('ttt.monitor.create_monitor', autospec=True) as monitor:
                cli.run()
                assert len(monitor.call_args_list)
                args, kwargs = monitor.call_args_list[0]
                assert kwargs['irc_server'] is None

    @patch('sys.argv', new=['ttt', 'watch_path',
        '--irc_server', 'testserver', '--irc_port', '6666',
        '--irc_channel', '#test', '--irc_nick', 'testtest'])
    def test_irc_enabled(self):
        context = MagicMock()
        with patch('ttt.systemcontext.create_context', return_value=context):
            with patch('ttt.monitor.create_monitor', autospec=True) as monitor:
                cli.run()
                assert len(monitor.call_args_list)
                args, kwargs = monitor.call_args_list[0]
                assert 'irc_server' in kwargs
                assert kwargs['irc_server'] == 'testserver'
                assert kwargs['irc_port'] == 6666
                assert kwargs['irc_channel'] == '#test'
                assert kwargs['irc_nick'] == 'testtest'
