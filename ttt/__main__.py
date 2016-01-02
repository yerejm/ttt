import sys
import colorama

from ttt import cli

if __name__ == "__main__":
    if sys.stdout.isatty():
        colorama.init()

    try:
        cli.run()
    except Exception as e:
        print(e)
        sys.exit(1)
    sys.exit(0)

