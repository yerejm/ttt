#!/bin/sh
PYENV_VERSION=3.6.0 pip install -r requirements.txt
PYENV_VERSION=3.6.0 pip install -r dev-requirements.txt

PYENV_VERSION=3.5.2 pip install -r requirements.txt
PYENV_VERSION=3.5.2 pip install -r dev-requirements.txt

PYENV_VERSION=2.7.13 pip install -r requirements-py27.txt
PYENV_VERSION=2.7.13 pip install -r dev-requirements-py27.txt

pyenv rehash
