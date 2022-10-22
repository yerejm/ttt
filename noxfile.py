import tempfile

import nox


nox.options.sessions = "lint", "tests"
locations = "src", "tests", "noxfile.py"
with open(".tool-versions") as f:
    versions_line = f.readline()
supported_pythons = [
    ".".join(version.split(".")[0:2]) for version in versions_line.split()[1:]
]
latest_python = supported_pythons[0]


def install_with_constraints(session, *args, **kwargs):
    with tempfile.NamedTemporaryFile() as requirements:
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
    with tempfile.NamedTemporaryFile() as requirements:
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
