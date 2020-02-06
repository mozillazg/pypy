============================
What's new in PyPy2.7 7.3.0+
============================

.. this is a revision shortly after release-pypy-7.3.0
.. startrev: 994c42529580

.. branch: cpyext-speedup-tests

Make cpyext test faster, especially on py3.6

.. branch: array-and-nan

Handle ``NAN`` more correctly in ``array.array`` for ``__eq__`` and ``count``

.. branch: bpo-16055

Fixes incorrect error text for ``int('1', base=1000)``

.. branch: record-known-result

Improve reasoning of the JIT about utf-8 index manipulation. Add a generic
framework to give hints that help the JIT reason about elidable calls and
more generically, other invariants of the code.
