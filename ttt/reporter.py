class Reporter(object):
    """
    Abstract base class describing the interface used by Monitor when notifying
    of events occurring during the watch/build/test cycle.
    """
    def session_start(self, session_descriptor):
        pass

    def session_end(self, session_descriptor, duration):
        pass

    def report_build_path(self):
        pass

    def report_watchstate(self, watchstate):
        pass

    def report_interrupt(self, interrupt):
        pass

    def wait_change(self):
        pass

    def report_build_failure(self):
        pass

    def report_results(self, results):
        pass

    def report_failures(self, results):
        pass

    def interrupt_detected(self):
        pass

    def halt(self):
        pass
