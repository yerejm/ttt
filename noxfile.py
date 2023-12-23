from operator import itemgetter
import os
import platform
from subprocess import Popen
from tempfile import NamedTemporaryFile

import nox

nox.options.sessions = "lint", "tests"
locations = "src", "tests", "noxfile.py"
if os.name == "nt":
    version_tuple = platform.python_version_tuple()
    latest_python = ".".join(version_tuple[:2])
    supported_pythons = [latest_python]
else:
    with NamedTemporaryFile(delete=False) as python_versions:
        proc = Popen(["asdf", "list", "python"], stdout=python_versions)
        proc.wait()
        python_versions.seek(0)
        installed_pythons = [
            version.decode("utf-8").strip().replace("*", "").split(".")
            for version in python_versions.readlines()
        ]
        installed_pythons.sort(reverse=True, key=itemgetter(0, 1, 2))
        supported_pythons = [
            "{}.{}".format(version[0], version[1])
            for version in installed_pythons
            if int(version[0]) > 2
        ]
        latest_python = supported_pythons[0]


def install_with_constraints(session, *args, **kwargs):
    requirements = None
    try:
        with NamedTemporaryFile(delete=False) as requirements:
            session.run(
                "poetry",
                "export",
                "--only",
                "dev",
                "--without-hashes",
                "--format=requirements.txt",
                f"--output={requirements.name}",
                external=True,
            )
            session.install("-r", requirements.name, *args, **kwargs)
    finally:
        if requirements:
            os.remove(requirements.name)


@nox.session(python=latest_python)
def black(session):
    args = session.posargs or locations
    install_with_constraints(session)
    session.run("black", *args)


@nox.session(python=supported_pythons)
def lint(session):
    args = session.posargs or locations
    install_with_constraints(session)
    session.run("flake8", *args)


@nox.session(python=latest_python)
def safety(session):
    requirements = None
    try:
        with NamedTemporaryFile(delete=False) as requirements:
            session.run(
                "poetry",
                "export",
                "--only",
                "dev",
                "--format=requirements.txt",
                "--without-hashes",
                f"--output={requirements.name}",
                external=True,
            )
            install_with_constraints(session)
            session.run(
                "safety", "check", f"--file={requirements.name}", "--full-report"
            )
    finally:
        if requirements:
            os.remove(requirements.name)


@nox.session(python=supported_pythons)
def tests(session):
    args = session.posargs or ["--cov", "-m", "not e2e"]
    session.run("poetry", "install", "--only", "main", external=True)
    install_with_constraints(session)
    session.run("pytest", *args)
