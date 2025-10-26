# -*- coding: utf-8 -*-

import sys

import colorama


try:
    from importlib.metadata import version, PackageNotFoundError
except ImportError:
    from importlib_metadata import version, PackageNotFoundError


try:
    __version__ = version(__name__)
except PackageNotFoundError:
    __version__ = "unknown"

if sys.stdout.isatty():
    colorama.init()

__progname__ = __name__
