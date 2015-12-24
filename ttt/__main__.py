import sys
import time

import colorama

from ttt import cmake
from ttt import watcher
from ttt import executor

RUNNING = 1
STOPPING = 2
FORCED_RUNNING = 3

def main():
    ctx = cmake.CMakeContext(sys.argv[1])

    watch_path = ctx.watch_path
    build_path = ctx.build_path
    w = watcher.Watcher(watch_path)
    t = executor.Executor(build_path)

    runstate = FORCED_RUNNING

    delay = 1
    while runstate != STOPPING:
        try:
            time.sleep(delay)

            watchstate = w.poll()
            if watchstate.has_changed() or runstate == FORCED_RUNNING:
                runstate = RUNNING
                ctx.build()
                t.test(w.filelist)

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

