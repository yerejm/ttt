#!/bin/sh
export PYENV_VERSION=$@
version=$(echo ${PYENV_VERSION} | cut -c 1-3)
pytest=py.test
if [ "${version}" != "3.5" ]; then
    pytest=py.test-2.7
fi
${pytest} -rw --lf -f --color=yes --cov ttt --cov-report term-missing test
