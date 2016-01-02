import sys
import colorama

from ttt import cli

if __name__ == "__main__":
    if sys.stdout.isatty():
        colorama.init()
    cli.run()
    sys.exit(0)

