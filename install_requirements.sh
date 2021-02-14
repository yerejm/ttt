#!/bin/sh
set -o pipefail
set -o errexit
pip install -r requirements.txt && pip install -r dev-requirements.txt
