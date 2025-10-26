import click

from ttt import monitor
from ttt.terminal import Terminal
from . import __progname__, __version__


@click.command()
@click.argument("watch_path", nargs=1, type=click.Path())
@click.argument(
    "filename",
    nargs=-1,
    default=monitor.DEFAULT_SOURCE_PATTERNS,
)
@click.option(
    "--build-path",
    type=click.Path(),
    help="Path to the build area. If not provided, it will be in a "
    "directory under the local path named {dir}-{config}-build "
    "where {dir} is the basename of the source path, and {config} "
    "is the build configuration. If provided and is relative, it "
    "will be created under the local path.",
)
@click.option(
    "--exclude",
    multiple=True,
    help="Exclude files and directories by name or by pattern."
    "Similar to include."
    "Repeatable.",
)
@click.option(
    "--generator",
    default=None,
    help="cmake generator: refer to cmake documentation",
)
@click.option(
    "--config", default="Debug", help="build configuration: e.g. Release, Debug."
)
@click.option(
    "--clean",
    "-c",
    is_flag=True,
    default=False,
    help="Always remove existing build area to ensure a clean build.",
)
@click.option(
    "--watch",
    "-w",
    is_flag=True,
    default=False,
    help="Enable watch mode - the watch, build, test cycle.",
)
@click.option(
    "--test",
    "-t",
    is_flag=True,
    default=False,
    help="Test after build. If given, -DENABLE_TESTS=ON is implied.",
)
@click.option(
    "--define",
    "-D",
    multiple=True,
    help="Passed through to CMake as-is as its -Dvar=value options." "Repeatable.",
)
@click.option("--verbosity", "-v", default=0, count=True, help="More v's more verbose.")
@click.version_option(version=__version__, prog_name=__progname__)
def ttt(
    watch_path,
    filename,
    build_path,
    exclude,
    generator,
    config,
    clean,
    watch,
    test,
    define,
    verbosity,
):
    """Watch, build, and test the WATCH_PATH source area given FILENAME patterns.

    The FILENAME items given are a series of file names or file name patterns
    to be watched. These are only truly meaningful when watch mode is enabled,
    otherwise they are identified only once.  When files identified by the file
    name or file name patterns are detected to have been added, changed, or
    deleted, this triggers a watch, build, test cycle. If not provided, files
    matching *.cc, *.c, *.h, and CMakeLists.txt are watched.

    Be aware of shell expansion!
    """
    Terminal.VERBOSITY = verbosity
    patterns = set(["".join(f) for f in filename])  # why join?
    if verbosity:
        print("Watching:")
        for p in patterns:
            print(p)
    if verbosity > 2:
        print(
            "Call arguments were:"
            f"watch_path={watch_path},"
            f"patterns={patterns},"
            f"build_path={build_path},"
            f"exclude={exclude},"
            f"generator={generator},"
            f"config={config},"
            f"clean={clean},"
            f"watch={watch},"
            f"test={test},"
            f"define={define},"
            f"verbosity={verbosity}"
        )
    m = monitor.create_monitor(
        watch_path=watch_path,
        patterns=patterns,
        build_path=build_path,
        exclude=exclude,
        generator=generator,
        config=config,
        clean=clean,
        watch=watch,
        test=test,
        define=define,
        verbosity=verbosity,
    )
    if watch:
        m.run()
    else:
        m.build()
        m.test()
