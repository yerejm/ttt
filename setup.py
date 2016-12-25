#!/usr/bin/env python
# -*- coding: utf-8 -*-

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup
import ast
import re

with open('README.rst') as readme_file:
    readme = readme_file.read()

_version_re = re.compile(r'__version__\s+=\s+(.*)')

with open('ttt/__init__.py', 'rb') as f:
    version = str(ast.literal_eval(_version_re.search(
        f.read().decode('utf-8')).group(1)))

    import sys

from setuptools.command.test import test as TestCommand


class PyTest(TestCommand):
    user_options = [('pytest-args=', 'a', "Arguments to pass to py.test")]

    def initialize_options(self):
        TestCommand.initialize_options(self)
        self.pytest_args = []

    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        #import here, cause outside the eggs aren't loaded
        import pytest
        errno = pytest.main(self.pytest_args)
        sys.exit(errno)

requirements = [
    'six',
    'python-termstyle',
    'colorama',
    'argh',
    'irc'
]
try:
    from os import scandir
except:
    requirements.append('scandir')

test_requirements = [
    'pytest',
    'pytest-xdist',
    'pytest-cov',
    'testfixtures'
]
try:
    import unittest.mock
except:
    test_requirements.append('mock')

setup(
    name='ttt',
    version=version,
    description="Watch, Build, Test",
    long_description=readme,
    author='yerejm',
    packages=[
        'ttt',
    ],
    package_dir={'ttt': 'ttt'},
    entry_points={
        'console_scripts': [
            'ttt = ttt.__main__:main'
        ]
    },
    include_package_data=True,
    install_requires=requirements,
    license="ISCL",
    keywords='ttt',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: ISC License (ISCL)',
        'Natural Language :: English',
        "Programming Language :: Python :: 2",
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ],
    test_suite='test',
    cmdclass = {'test': PyTest},
    tests_require=test_requirements,
)
