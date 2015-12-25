import os
import stat
import subprocess
from ttt import subproc

class SystemContext(object):
    def walk(self, root_directory):
        try:
            from os import scandir, walk
        except ImportError:
            try:
                from scandir import scandir, walk
            except ImportError:
                from os import walk
        for dirpath, _, filelist in walk(root_directory):
            for filename in filelist:
                path = os.path.join(dirpath, filename)
                statmode = os.stat(path).st_mode
                if stat.S_ISREG(statmode):
                    yield dirpath, filename, statmode

    def execute(self, *args, **kwargs):
        if 'universal_newlines' not in kwargs:
            kwargs['universal_newlines'] = True
        return subprocess.check_output(*args, **kwargs).splitlines()

    def checked_call(self, *args, **kwargs):
        if 'universal_newlines' not in kwargs:
            kwargs['universal_newlines'] = True
        subprocess.check_call(*args, **kwargs)

    def glob_files(self, build_path, selector):
        for dirpath, filename, statmode in self.walk(build_path):
            if selector(filename):
                yield dirpath, filename, statmode

    def streamed_call(self, *args, **kwargs):
        if 'universal_newlines' not in kwargs:
            kwargs['universal_newlines'] = True
        return subproc.call_output(*args, **kwargs)

