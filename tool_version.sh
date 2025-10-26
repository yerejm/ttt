#!/bin/sh
set -eux -o pipefail
echo "python $(mise ls python | awk '{ver=(NR==1?ver:ver " ")$2}END{print ver}')" > .tool-versions
