===============================
ttt
===============================

------
Run As
------

^^^^^^^^^^
Executable
^^^^^^^^^^

Install: ``brew tap yerejm/tools && brew install ttt``

Then: ``ttt source_path``

^^^^^^
Module
^^^^^^

Install dependencies: ``poetry install`` (run inside ``poetry shell``)

Then: ``PYTHONPATH=/path/to/ttt:$PYTHONPATH python -m ttt source_path``

-------
Caveats
-------

Handling of stdout and stderr from the test execution don't work perfectly, but
are good enough for most cases.

