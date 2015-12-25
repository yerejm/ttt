import os
import stat
import subprocess

class SystemContext(object):
    def __init__(self, root_directory):
        self.root_directory = root_directory

    def walk(self):
        try:
            from os import scandir, walk
        except ImportError:
            try:
                from scandir import scandir, walk
            except ImportError:
                from os import walk
        for dirpath, _, filelist in walk(self.root_directory):
            for filename in filelist:
                path = os.path.join(dirpath, filename)
                statmode = os.stat(path).st_mode
                if stat.S_ISREG(statmode):
                    yield dirpath, filename, statmode

    def execute(self, *args, **kwargs):
        if 'universal_newlines' not in kwargs:
            kwargs['universal_newlines'] = True
        return subprocess.check_output(*args, **kwargs)

