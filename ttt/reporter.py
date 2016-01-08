import os
import termstyle

def create_reporter(context, watch_path=None, build_path=None):
    return Reporter(context, watch_path, build_path)

class Reporter(object):

    def __init__(self, context, watch_path, build_path):
        self.context = context
        self._watch_path = watch_path
        self._build_path = build_path

    def session_start(self, session_descriptor):
        self.writeln('{} session starts'.format(session_descriptor), decorator=[termstyle.bold], pad='=')

    def report_build_path(self):
        self.writeln('### Building:   {}'.format(self._build_path), decorator=[termstyle.bold])

    def report_watchstate(self, watchstate):
        def report_changes(change, filelist, decorator=[]):
            for f in filelist:
                self.writeln('# {} {}'.format(change, f), decorator=decorator)

        report_changes('CREATED', watchstate.inserts, [termstyle.green])
        report_changes('MODIFIED', watchstate.updates, [termstyle.yellow])
        report_changes('DELETED', watchstate.deletes, [termstyle.red])
        self.writeln('### Scan time: {:10.3f}s'.format(watchstate.walk_time))

    def report_interrupt(self, interrupt):
        self.writeln(interrupt.__class__.__name__, pad='!')

    def wait_change(self):
        self.writeln('waiting for changes',
                decorator=[termstyle.bold], pad='#')
        self.writeln('### Watching:   {}'.format(self._watch_path),
                decorator=[termstyle.bold])

    def report_results(self, results):
        shortstats = '{} passed in {} seconds'.format(
                results['total_passed'],
                results['total_runtime']
                )
        total_failed = results['total_failed']
        if total_failed > 0:
            self.report_failures(results['failures'])
            self.writeln('{} failed, {}'.format(total_failed, shortstats),
                    decorator=[termstyle.red,termstyle.bold], pad='=')
        else:
            self.writeln(shortstats,
                    decorator=[termstyle.green,termstyle.bold], pad='=')

    def report_failures(self, results):
        self.writeln('FAILURES', pad='=')
        for testname, out, err in results:
            self.writeln(testname,
                    decorator=[termstyle.red, termstyle.bold], pad='_')
            test_output_pos = find_source_file_line(out, self._watch_path)
            results = out[test_output_pos:]
            self.writeln(os.linesep.join(results))

            extra_out = out[:test_output_pos]
            if extra_out:
                self.writeln('Additional output', pad='-')
                self.writeln(os.linesep.join(extra_out))

            if self._watch_path is None:
                locator = results[0]
            else:
                locator = strip_path(results[0], self._watch_path)
            self.writeln(strip_trailer(locator),
                    decorator=[termstyle.red, termstyle.bold], pad='_')

    def interrupt_detected(self):
        self.writeln()
        self.writeln("Interrupt again to exit.")

    def halt(self):
        self.writeln()
        self.writeln("Watching stopped.")

    def writeln(self, *args, **kwargs):
        self.context.writeln(*args, **kwargs)

def strip_path(string, path):
    realpath = path
    if realpath not in string:
        realpath = os.path.realpath(path)
    if realpath in string:
        return string[len(realpath) + 1:]
    else:
        return string

def find_source_file_line(lines, path):
    if path is not None:
        for i, l in enumerate(lines):
            if path in l:
                return i
    return 0

def strip_trailer(string):
    return string[:string.find(' ') - 1]
