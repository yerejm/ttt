from operator import itemgetter
import os
import platform
from tempfile import NamedTemporaryFile

import nox

nox.options.sessions = "lint", "tests"
locations = "src", "tests", "noxfile.py"
if platform.system() == "Windows":
    version_tuple = platform.python_version_tuple()
    latest_python = ".".join(version_tuple[:2])
    supported_pythons = [latest_python]
else:
    with open(".tool-versions") as tool_versions:
        installed_pythons = []
        for line in tool_versions.readlines():
            if line.startswith("python"):
                python_versions = line.strip().split()
                for version in python_versions[1:]:
                    vl = version.split(".")
                    ivs = [int(v) for v in vl]
                    installed_pythons.append(ivs)
                break
        installed_pythons.sort(reverse=True, key=itemgetter(0, 1, 2))
        supported_pythons = [
            "{}.{}".format(version[0], version[1])
            for version in installed_pythons
            if int(version[0]) > 2
        ]
        latest_python = supported_pythons[0]


def install_requirements(session, *args, **kwargs):
    # windows workaround for NamedTemporaryFile behaving differently compared
    # to macos/linux for session run/install
    requirements = None
    try:
        with NamedTemporaryFile(delete=False) as requirements:
            session.run(
                "uv",
                "export",
                "--quiet",
                "--only-dev",
                "--format",
                "requirements.txt",
                "--output-file",
                requirements.name,
                external=True,
            )
            session.install("--quiet", "-r", requirements.name, *args, **kwargs)
    finally:
        if requirements:
            os.remove(requirements.name)


@nox.session(python=latest_python)
def black(session):
    args = session.posargs or locations
    install_requirements(session)
    session.run("black", *args)


@nox.session(python=latest_python)
def lint(session):
    args = session.posargs or locations
    install_requirements(session)
    session.run("flake8", *args)


@nox.session(python=supported_pythons, venv_backend="uv")
def tests(session):
    args = session.posargs or ["--cov", "-m", "not e2e"]
    install_requirements(session)

    session.install(
        "pytest-xdist",
        "pytest-randomly",
        "pytest-sugar",
    )

    session.run(
        "pytest",
        # "-v",  # verbose output - interferes with some tests
        "-s",  # don't capture output
        "--tb=short",  # shorter traceback format
        "--strict-markers",  # treat unregistered markers as errors
        "-n",
        "auto",  # parallel testing
        *args,  # allows passing additional pytest args from command line
    )
