#!/bin/sh
set -eux -o pipefail
echo "python $(mise ls python | grep -v missing | awk '{ver=(NR==1?ver:ver " ")$2}END{print ver}')" > .tool-versions
uv tool install nox
