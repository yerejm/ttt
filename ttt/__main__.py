import os
import sys
import colorama

from ttt import systemcontext
from ttt import monitor

def main():
    watch_path = os.path.abspath(sys.argv[1])
    if not os.path.exists(watch_path):
        print("Invalid cmake source path.")
        sys.exit(1)

    m = monitor.Monitor(watch_path, systemcontext.SystemContext())
    m.activate(1)

    sys.exit(0)

if __name__ == "__main__":
    colorama.init()
    main()

