==================
PyPy3 2.1.0 beta 1
==================

We're pleased to announce the first beta of the upcoming 2.1.0 release of
PyPy3. This is the first release of PyPy which targets Python 3.2
compatibility.

We would like to thank all of the people who donated_ to the `py3k proposal`_
for supporting the work that went into this and future releases.

You can download the PyPy3 2.1.0 beta 1 release here:

    http://pypy.org/download.html

Highlights
==========

* The first release of PyPy3: support for Python 3, targetting CPython 3.2.3!
  Albeit with a few missing features:

  - The stdlib test_memoryview includes some failing tests (marked to
    skip) and test_multiprocessing is known to deadlock on some
    platforms

  - There are some known performance regressions (issues `#1540`_ &
    `#1541`_) slated to be resolved before the final release

  - NumPyPy is currently disabled

What is PyPy3?
==============

PyPy3 is a very compliant Python interpreter, almost a drop-in replacement for
CPython 3.2.3. It's fast due to its integrated tracing JIT compiler.

This release supports x86 machines running Linux 32/64, Mac OS X 64 or Windows
32. However Windows 32 support could use some improvement.

Windows 64 work is still stalling and we would welcome a volunteer to handle
that.

How to use PyPy3?
=================

We suggest using PyPy from a `virtualenv`_. Once you have a virtualenv
installed, you can follow instructions from `pypy documentation`_ on how
to proceed. This document also covers other `installation schemes`_.

.. _donated: http://morepypy.blogspot.com/2012/01/py3k-and-numpy-first-stage-thanks-to.html
.. _`py3k proposal`: http://pypy.org/py3donate.html
.. _`#1540`: https://bugs.pypy.org/issue1540
.. _`#1541`: https://bugs.pypy.org/issue1541
.. _`pypy documentation`: http://doc.pypy.org/en/latest/getting-started.html#installing-using-virtualenv
.. _`virtualenv`: http://www.virtualenv.org/en/latest/
.. _`installation schemes`: http://doc.pypy.org/en/latest/getting-started.html#installing-pypy


Cheers,
the PyPy team
