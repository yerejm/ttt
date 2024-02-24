#!/bin/sh
set -eux -o pipefail
echo "python $(asdf list python 3 | sort -V -r -b | sed 's/ //g' | paste -sd' ' -)" > .tool-versions
