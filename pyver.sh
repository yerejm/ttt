#!/bin/sh
pyenv versions 2>/dev/null | grep 3 | awk "{print $1}" > .python-version
