#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
test_monitor
----------------------------------

Tests for `monitor` module.
"""
import os
import termstyle

from ttt.systemcontext import SystemContext
from ttt.monitor import Monitor
from ttt.monitor import Reporter

class MockContext(SystemContext):
    def __init__(self):
        self.output = ''

    def getvalue(self):
        return self.output

    def write(self, string):
        self.output += string

    def walk(self, root):
        return []

    def write(self, string):
        self.output += string

class TestMonitor:
    def test_init(self):
        c = MockContext()
        m = Monitor('/path/to/watch', c, interval=0)

        assert m.runstate.active()

    def test_interrupt(self):
        c = MockContext()
        m = Monitor('/path/to/watch', c, interval=0)

        m.handle_keyboard_interrupt()
        assert m.runstate.active()
        assert m.runstate.allowed_once()
        assert not m.runstate.allowed_once()

class TestReporter:
    def test_session_start(self):
        m = MockContext()
        r = Reporter(m)

        r.session_start()
        m.getvalue() == termstyle.bold(
                ''.ljust(30, '=') +
                ' test session starts ' +
                ''.ljust(31, '=')
                ) + os.linesep

    def test_wait_change(self):
        m = MockContext()
        r = Reporter(m)

        r.wait_change('watch_path')
        m.getvalue() == termstyle.bold(
                    ''.ljust(29, '#') +
                    ' waiting for changes ' +
                    ''.ljust(30, '#')
                ) + os.linesep + termstyle.bold(
                    ' ### Watching:   watch_path'
                )+ os.linesep

    def test_report_all_passed(self):
        m = MockContext()
        r = Reporter(m)

        results = {
                'total_runtime': 2.09,
                'total_passed': 1,
                'total_failed': 0,
                'failures': []
                }
        r.report_results(results)
        m.getvalue() == termstyle.bold(termstyle.green(
                    ''.ljust(27, '=') +
                    ' 1 passed in 2.09 seconds ' +
                    ''.ljust(27, '=')
                )) + os.linesep

    def test_report_all_failed(self):
        m = MockContext()
        r = Reporter(m)

        results = {
                'total_runtime': 2.09,
                'total_passed': 0,
                'total_failed': 1,
                'failures': [
                    [ 'fail1', [
                        'results line 1',
                        'results line 2',
                        'results line 3',
                        'results line 4',
                        ] 
                    ],
                ]
            }
        r.report_results(results)
        expected = [
            '=================================== FAILURES ===================================',
            termstyle.bold(termstyle.red(
            '____________________________________ fail1 _____________________________________'
            )),
            'results line 2',
            'results line 3',
            'results line 4',
            '',
            'results line 1',
            termstyle.bold(termstyle.red(
            '====================== 1 failed, 0 passed in 2.09 seconds ======================'
            )),
            ]
        actual = m.getvalue().splitlines()
        assert actual == expected

    def test_report_multiple_failed(self):
        m = MockContext()
        r = Reporter(m)

        results = {
                'total_runtime': 2.09,
                'total_passed': 0,
                'total_failed': 2,
                'failures': [
                    [ 'fail1', [
                        'results line 1',
                        'results line 2',
                        'results line 3',
                        'results line 4',
                        ] 
                    ],
                    [ 'fail2', [
                        'results line 1',
                        'results line 2',
                        'results line 3',
                        'results line 4',
                        ] 
                    ],
                ]
            }
        r.report_results(results)
        expected = [
            '=================================== FAILURES ===================================',
            termstyle.bold(termstyle.red(
            '____________________________________ fail1 _____________________________________'
            )),
            'results line 2',
            'results line 3',
            'results line 4',
            '',
            'results line 1',
            termstyle.bold(termstyle.red(
            '____________________________________ fail2 _____________________________________'
            )),
            'results line 2',
            'results line 3',
            'results line 4',
            '',
            'results line 1',
            termstyle.bold(termstyle.red(
            '====================== 2 failed, 0 passed in 2.09 seconds ======================'
            )),
            ]
        actual = m.getvalue().splitlines()
        assert actual == expected

    def test_report_changes(self):
        m = MockContext()
        r = Reporter(m)

        r.report_changes('TEST', ['test'])
        assert m.getvalue() == '# TEST test' + os.linesep

    def test_interrupt_detected(self):
        m = MockContext()
        r = Reporter(m)

        r.interrupt_detected()
        assert m.getvalue() == os.linesep + 'Interrupt again to exit.' + os.linesep

    def test_halt(self):
        m = MockContext()
        r = Reporter(m)

        r.halt()
        assert m.getvalue() == os.linesep + 'Watching stopped.' + os.linesep
