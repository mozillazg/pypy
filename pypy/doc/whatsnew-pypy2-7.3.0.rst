==========================
What's new in PyPy2.7 7.3+
==========================

.. this is a revision shortly after release-pypy-7.2.0
.. startrev: a511d86377d6 

.. branch: fix-descrmismatch-crash

Fix segfault when calling descr-methods with no arguments


.. branch: record-known-result

Improve reasoning of the JIT about utf-8 index manipulation. Add a generic
framework to give hints that help the JIT reason about elidable calls and
more generically, other invariants of the code.
