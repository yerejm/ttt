#!/bin/sh
poetry run pytest -rw --lf -f --color=yes --cov ttt --cov-report term-missing
