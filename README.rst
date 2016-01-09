===============================
ttt
===============================

------
Run As
------

^^^^^^
Module
^^^^^^

For Python 3.5: ``pip install -r requirements.txt``

For Python 2.7: ``pip install -r requirements-py27.txt``

Then: ``PYTHONPATH=/path/to/ttt:$PYTHONPATH python -m ttt source_path``

^^^^^^^^^^
Executable
^^^^^^^^^^

Install: ``python setup.py install``

Then: ``ttt source_path``

-----
Notes
-----

Installation of the ``scandir`` module for Python 2.7 requires compilation.

-------
Caveats
-------

Handling of stdout and stderr from the test execution don't work perfectly, but
are good enough for most cases.

