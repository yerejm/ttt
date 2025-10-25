"""
ttt.termstyle
~~~~~~~~~~~~
this module provides terminal styles
:copyright: (c) yerejm
"""

from colorama import Fore, Style


def red(text):
    return Fore.RED + text + Style.RESET_ALL


def yellow(text):
    return Fore.YELLOW + text + Style.RESET_ALL


def green(text):
    return Fore.GREEN + text + Style.RESET_ALL


def bold(text):
    return Style.BRIGHT + text + Style.RESET_ALL
