#!/bin/sh
pyenv local $@
py.test --lf -f --color=yes --cov ttt --cov-report term-missing test
