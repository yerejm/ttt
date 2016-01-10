import sys
import colorama

from ttt import cli


def main():
    if sys.stdout.isatty():
        colorama.init()
    cli.run()
    sys.exit(0)


if __name__ == "__main__":
    main()
