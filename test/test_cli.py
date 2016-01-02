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

    @patch('sys.argv', new=['ttt', 'watch_path', '-b', 'buildpath', '-g', 'Ninja', '-v'])
    def test_args(self):
        context = MagicMock()
        with patch('ttt.systemcontext.create_context', return_value=context):
            with patch('ttt.monitor.create_monitor', autospec=True) as monitor:
                cli.run()
                assert monitor.call_args_list == [
                    call(context, 'watch_path', build_path='buildpath', generator='Ninja', verbosity=1)
                ]

    @patch('sys.argv', new=['ttt', 'watch_path', '-vv'])
    def test_verbosity(self):
        context = MagicMock()
        with patch('ttt.systemcontext.create_context', return_value=context):
            with patch('ttt.monitor.create_monitor', autospec=True) as monitor:
                cli.run()
                assert monitor.call_args_list == [
                    call(context, 'watch_path', build_path=None, generator=None, verbosity=2)
                ]
