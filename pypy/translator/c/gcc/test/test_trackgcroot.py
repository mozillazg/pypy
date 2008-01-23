import py
import sys
from pypy.translator.c.gcc.trackgcroot import GcRootTracker
from pypy.translator.c.gcc.trackgcroot import FunctionGcRootTracker
from StringIO import StringIO


def test_find_functions():
    source = """\
\t.p2align 4,,15
.globl pypy_g_make_tree
\t.type\tpypy_g_make_tree, @function
\tFOO
\t.size\tpypy_g_make_tree, .-pypy_g_make_tree

\t.p2align 4,,15
.globl pypy_fn2
\t.type\tpypy_fn2, @function
\tBAR
\t.size\tpypy_fn2, .-pypy_fn2
\tMORE STUFF
"""
    lines = source.splitlines(True)
    parts = list(GcRootTracker().find_functions(iter(lines)))
    assert len(parts) == 5
    assert parts[0] == (False, lines[:2])
    assert parts[1] == (True,  lines[2:5])
    assert parts[2] == (False, lines[5:8])
    assert parts[3] == (True,  lines[8:11])
    assert parts[4] == (False, lines[11:])
