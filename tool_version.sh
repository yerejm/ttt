#!/bin/sh
set -eux -o pipefail
echo "python $(mise exec python@3.13 -- python --version | awk '{print $2}')" > .tool-versions
