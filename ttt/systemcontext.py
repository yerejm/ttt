import os
import stat
import subprocess
from ttt import subproc

try:
    from os import scandir, walk
except ImportError:
    try:
        from scandir import scandir, walk
    except ImportError:
        from os import walk

class SystemContext(object):
    def walk(self, root_directory):
        for dirpath, _, filelist in walk(root_directory):
            for filename in filelist:
                path = os.path.join(dirpath, filename)
                statmode = os.stat(path).st_mode
                if stat.S_ISREG(statmode):
                    yield dirpath, filename, statmode

    def glob_files(self, build_path, selector):
        for dirpath, filename, statmode in self.walk(build_path):
            if selector(filename):
                yield dirpath, filename, statmode

    def execute(self, *args, **kwargs):
        return subprocess.check_output(*args, **kwargs).splitlines()

    def checked_call(self, *args, **kwargs):
        return subprocess.check_call(*args, **kwargs)

    def streamed_call(self, *args, **kwargs):
        return subproc.call_output(*args, **kwargs)

