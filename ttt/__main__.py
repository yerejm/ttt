import sys
import time

from ttt import cmake
from ttt import watcher
from ttt import tester

RUNNING = 1
STOPPING = 2
FORCED_RUNNING = 3

def main():
    ctx = cmake.CMakeContext(sys.argv[1])

    watch_path = ctx.watch_path
    build_path = ctx.build_path
    w = watcher.Watcher(watch_path)
    t = tester.Tester(build_path)

    runstate = FORCED_RUNNING

    delay = 1
    while runstate != STOPPING:
        try:
            time.sleep(delay)

            if w.poll() or runstate == FORCED_RUNNING:
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
    main()

