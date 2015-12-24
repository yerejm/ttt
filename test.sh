#!/bin/sh
export PYENV_VERSION=$@
version=$(echo ${PYENV_VERSION} | cut -c 1-3)
pytest=py.test
${pytest} -rw --lf -f --color=yes --cov ttt --cov-report term-missing test
