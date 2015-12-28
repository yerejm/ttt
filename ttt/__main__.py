import os
import sys
import colorama

from ttt import systemcontext
from ttt import monitor

def abswatchpath(path):
    watch_path = os.path.abspath(path)
    if not os.path.exists(watch_path):
        print("Invalid cmake source path.")
        sys.exit(1)
    return watch_path

if __name__ == "__main__":
    colorama.init()
    monitor.Monitor(abswatchpath(sys.argv[1]), systemcontext.SystemContext()).run()
    sys.exit(0)

