import sys
import os
import time

import colorama

from ttt import cmake
from ttt import watcher
from ttt import executor
from ttt import systemcontext

RUNNING, STOPPING, FORCED_RUNNING = range(3)
DEFAULT_BUILD_PATH_SUFFIX = '-build'

def make_build_path(watch_path, suffix=DEFAULT_BUILD_PATH_SUFFIX):
    return os.path.join(
        os.getcwd(),
        "{}{}".format(os.path.basename(watch_path), suffix)
    )

def main():
    watch_path = os.path.abspath(sys.argv[1])
    build_path = make_build_path(watch_path)

    sc = systemcontext.SystemContext()
    ctx = cmake.CMakeContext(sc)

    w = watcher.Watcher(sc)
    t = executor.Executor(sc)

    runstate = FORCED_RUNNING

    delay = 1
    while runstate != STOPPING:
        try:
            time.sleep(delay)

            watchstate = w.poll(watch_path)
            if watchstate.has_changed() or runstate == FORCED_RUNNING:
                runstate = RUNNING
                ctx.build(watch_path, build_path)
                t.test(build_path, w.testlist())

        except KeyboardInterrupt:
            test_filter = []
            if runstate == FORCED_RUNNING:
                runstate = STOPPING
            else:
                runstate = FORCED_RUNNING
                print("\nInterrupt again to exit.")
    print("\nWatching stopped.")

if __name__ == "__main__":
    colorama.init()
    main()

