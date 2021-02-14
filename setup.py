#!/usr/bin/env python
# -*- coding: utf-8 -*-

import ast
import re
import sys

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup
from setuptools.command.test import test as TestCommand


requirements = ["six", "python-termstyle", "colorama", "argh", "irc==16.0"]
test_requirements = ["pytest", "pytest-xdist", "pytest-cov", "testfixtures"]


try:
    import unittest.mock

    _mock = unittest.mock
except ImportError:
    test_requirements.append("mock")


class PyTest(TestCommand):
    user_options = [("pytest-args=", "a", "Arguments to pass to py.test")]

    def initialize_options(self):
        TestCommand.initialize_options(self)
        self.pytest_args = []

    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        # import here, because outside the eggs aren't loaded
        import pytest

        errno = pytest.main(self.pytest_args)
        sys.exit(errno)


_version_re = re.compile(r"version\s+=\s+(.*)")
version = "???"
with open("pyproject.toml", "rb") as f:
    version = str(
        ast.literal_eval(_version_re.search(f.read().decode("utf-8")).group(1))
    )

with open("README.rst") as readme_file:
    readme = readme_file.read()


setup(
    name="ttt",
    version=version,
    url="https://github.com/yerejm/ttt",
    description="Watch, Build, Test",
    long_description=readme,
    author="yerejm",
    packages=["ttt"],
    package_dir={"": "src"},
    entry_points={"console_scripts": ["ttt = ttt.__main__:main"]},
    include_package_data=True,
    install_requires=requirements,
    license="ISCL",
    keywords=["ttt"],
    classifiers=[
        "Environment :: Console",
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: ISC License (ISCL)",
        "Natural Language :: English",
        "Programming Language :: Python :: 3",
    ],
    test_suite="test",
    cmdclass={"test": PyTest},
    tests_require=test_requirements,
)
