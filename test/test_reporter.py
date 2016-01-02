#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
test_reporter
----------------------------------

Tests for `reporter` module.
"""
import os
import termstyle

from ttt.systemcontext import SystemContext
from ttt.monitor import create_reporter

class MockContext(SystemContext):
    def __init__(self):
        super(MockContext, self).__init__()
        self.output = ''

    def getvalue(self):
        return self.output

    def write(self, string):
        self.output += string

class TestReporter:
    def test_session_start(self):
        m = MockContext()
        r = create_reporter(m)

        r.session_start('test')
        assert m.getvalue() == termstyle.bold(
                ''.ljust(29, '=') +
                ' test session starts ' +
                ''.ljust(30, '=')
                ) + os.linesep

    def test_wait_change(self):
        m = MockContext()
        r = create_reporter(m, 'watch_path')

        r.wait_change()
        assert m.getvalue() == termstyle.bold(
                    ''.ljust(29, '#') +
                    ' waiting for changes ' +
                    ''.ljust(30, '#')
                ) + os.linesep + termstyle.bold(
                    '### Watching:   watch_path'
                ) + os.linesep

    def test_report_all_passed(self):
        m = MockContext()
        r = create_reporter(m)

        results = {
                'total_runtime': 2.09,
                'total_passed': 1,
                'total_failed': 0,
                'failures': []
                }
        r.report_results(results)
        assert m.getvalue() == termstyle.bold(termstyle.green(
                    ''.ljust(27, '=') +
                    ' 1 passed in 2.09 seconds ' +
                    ''.ljust(27, '=')
                )) + os.linesep

    def test_report_all_failed(self):
        m = MockContext()
        r = create_reporter(m, '/path')

        results = {
                'total_runtime': 2.09,
                'total_passed': 0,
                'total_failed': 1,
                'failures': [
                    [ 'fail1', [
                        '/path/to/file:12: blah',
                        'results line 2',
                        'results line 3',
                        'results line 4',
                        ], []
                    ],
                ]
            }
        r.report_results(results)
        expected = [
            '=================================== FAILURES ===================================',
            termstyle.bold(termstyle.red(
            '____________________________________ fail1 _____________________________________'
            )),
            '/path/to/file:12: blah',
            'results line 2',
            'results line 3',
            'results line 4',
            termstyle.bold(termstyle.red(
            '__________________________________ to/file:12 __________________________________'
            )),
            termstyle.bold(termstyle.red(
            '====================== 1 failed, 0 passed in 2.09 seconds ======================'
            )),
            ]
        actual = m.getvalue().splitlines()
        assert actual == expected

    def test_report_multiple_failed(self):
        m = MockContext()
        r = create_reporter(m, '/path')

        results = {
                'total_runtime': 2.09,
                'total_passed': 0,
                'total_failed': 2,
                'failures': [
                    [ 'fail1', [
                        '/path/to/file:12: blah',
                        'results line 2',
                        'results line 3',
                        'results line 4',
                        ], []
                    ],
                    [ 'fail2', [
                        '/path/to/file:102: blah',
                        'results line 2',
                        'results line 3',
                        'results line 4',
                        ], []
                    ],
                ]
            }
        r.report_results(results)
        expected = [
            '=================================== FAILURES ===================================',
            termstyle.bold(termstyle.red(
            '____________________________________ fail1 _____________________________________'
            )),
            '/path/to/file:12: blah',
            'results line 2',
            'results line 3',
            'results line 4',
            termstyle.bold(termstyle.red(
            '__________________________________ to/file:12 __________________________________'
            )),
            termstyle.bold(termstyle.red(
            '____________________________________ fail2 _____________________________________'
            )),
            '/path/to/file:102: blah',
            'results line 2',
            'results line 3',
            'results line 4',
            termstyle.bold(termstyle.red(
            '_________________________________ to/file:102 __________________________________'
            )),
            termstyle.bold(termstyle.red(
            '====================== 2 failed, 0 passed in 2.09 seconds ======================'
            )),
            ]
        actual = m.getvalue().splitlines()
        assert actual == expected

    def test_report_watchstate(self):
        m = MockContext()
        r = create_reporter(m)

        from ttt.watcher import WatchState
        r.report_watchstate(WatchState(['create'], ['delete'], ['modify'], 1.0))
        assert m.getvalue() == os.linesep.join([
                termstyle.green('# CREATED create'),
                termstyle.yellow('# MODIFIED modify'),
                termstyle.red('# DELETED delete'),
                '### Scan time:      1.000s',
                ]) + os.linesep

    def test_interrupt_detected(self):
        m = MockContext()
        r = create_reporter(m)

        r.interrupt_detected()
        assert m.getvalue() == os.linesep + 'Interrupt again to exit.' + os.linesep

    def test_halt(self):
        m = MockContext()
        r = create_reporter(m)

        r.halt()
        assert m.getvalue() == os.linesep + 'Watching stopped.' + os.linesep

    def test_report_build_path(self):
        m = MockContext()
        r = create_reporter(m, 'watch_path', 'build_path')

        r.report_build_path()
        assert m.getvalue() == termstyle.bold('### Building:   build_path') + os.linesep

    def test_report_interrupt(self):
        m = MockContext()
        r = create_reporter(m, 'watch_path', 'build_path')

        try:
            raise KeyboardInterrupt()
        except KeyboardInterrupt as e:
            r.report_interrupt(e)

        assert m.getvalue() == (
                ''.ljust(30, '!') +
                    ' KeyboardInterrupt ' +
                    ''.ljust(31, '!')
                + os.linesep
                )

    def test_report_with_stdout_and_stderr(self):
        m = MockContext()
        r = create_reporter(m, '/path')

        results = {
                'total_runtime': 2.09,
                'total_passed': 0,
                'total_failed': 1,
                'failures': [
                    [
                        'fail1',
                        [
                            'extra line 1',
                            'extra line 2',
                            '/path/to/file:12: blah',
                            'results line 1',
                            'results line 2',
                            'results line 3',
                        ],
                        [
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
            '/path/to/file:12: blah',
            'results line 1',
            'results line 2',
            'results line 3',
            '------------------------------ Additional output -------------------------------',
            'extra line 1',
            'extra line 2',
            termstyle.bold(termstyle.red(
            '__________________________________ to/file:12 __________________________________'
            )),
            termstyle.bold(termstyle.red(
            '====================== 1 failed, 0 passed in 2.09 seconds ======================'
            )),
            ]
        actual = m.getvalue().splitlines()
        assert actual == expected


    def test_path_stripping(self):
        m = MockContext()
        r = create_reporter(m, '/path/to/watch', '/path/to/build')

        failures = [[
                        'core.ok',
                        [
                            '/path/to/watch/test/test_core.cc:12: Failure',
                            'Value of: 2',
                            'Expected: ok()',
                            'Which is: 42',
                        ],
                        [
                        ]
                    ]]
        r.report_failures(failures)
        expected = [
            '=================================== FAILURES ===================================',
            termstyle.bold(termstyle.red(
            '___________________________________ core.ok ____________________________________'
            )),
            '/path/to/watch/test/test_core.cc:12: Failure',
            'Value of: 2',
            'Expected: ok()',
            'Which is: 42',
            termstyle.bold(termstyle.red(
            '_____________________________ test/test_core.cc:12 _____________________________',
            )),
            ]
        actual = m.getvalue().splitlines()
        assert actual == expected

