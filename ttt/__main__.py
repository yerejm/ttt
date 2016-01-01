import sys

from ttt import cli

if __name__ == "__main__":
    try:
        cli.run()
    except Exception as e:
        print(e)
        sys.exit(1)
    sys.exit(0)

