===============================
ttt
===============================

------
Run As
------

^^^^^^
Module
^^^^^^

Install dependencies: ``pip install -r requirements.txt``

Then: ``PYTHONPATH=/path/to/ttt:$PYTHONPATH python -m ttt source_path``

^^^^^^^^^^
Executable
^^^^^^^^^^

Install: ``python setup.py install``

Then: ``ttt source_path``

-------
Caveats
-------

Handling of stdout and stderr from the test execution don't work perfectly, but
are good enough for most cases.

