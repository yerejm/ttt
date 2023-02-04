from operator import itemgetter
from subprocess import Popen
from tempfile import NamedTemporaryFile

import nox


nox.options.sessions = "lint", "tests"
locations = "src", "tests", "noxfile.py"
with NamedTemporaryFile() as python_versions:
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
    with NamedTemporaryFile() as requirements:
        session.run(
            "poetry",
            "export",
            "--with",
            "dev",
            "--without-hashes",
            "--format=requirements.txt",
            f"--output={requirements.name}",
            external=True,
        )
        session.install(f"--constraint={requirements.name}", *args, **kwargs)


@nox.session(python=latest_python)
def black(session):
    args = session.posargs or locations
    install_with_constraints(
        session,
        "black",
    )
    session.run("black", *args)


@nox.session(python=supported_pythons)
def lint(session):
    args = session.posargs or locations
    install_with_constraints(
        session,
        "flake8",
        "flake8-bandit",
        "flake8-black",
        "flake8-bugbear",
        "flake8-import-order",
    )
    session.run("flake8", *args)


@nox.session(python=latest_python)
def safety(session):
    with NamedTemporaryFile() as requirements:
        session.run(
            "poetry",
            "export",
            "--with",
            "dev",
            "--format=requirements.txt",
            "--without-hashes",
            f"--output={requirements.name}",
            external=True,
        )
        install_with_constraints(
            session,
            "safety",
        )
        session.run("safety", "check", f"--file={requirements.name}", "--full-report")


@nox.session(python=supported_pythons)
def tests(session):
    args = session.posargs or ["--cov", "-m", "not e2e"]
    session.run("poetry", "install", "--with", "main", external=True)
    install_with_constraints(
        session,
        "coverage",
        "pytest",
        "pytest-cov",
        "pytest-mock",
        "testfixtures",
    )
    session.run("pytest", *args)
