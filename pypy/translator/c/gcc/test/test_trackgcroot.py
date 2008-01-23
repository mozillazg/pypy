import py
import sys, re
from pypy.translator.c.gcc.trackgcroot import GcRootTracker
from pypy.translator.c.gcc.trackgcroot import FunctionGcRootTracker
from StringIO import StringIO

this_dir = py.path.local(__file__).dirpath()


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


def test_computegcmaptable():
    tests = []
    for path in this_dir.listdir("track*.s"):
        n = path.purebasename[5:]
        try:
            n = int(n)
        except ValueError:
            pass
        tests.append((n, path))
    tests.sort()
    for _, path in tests:
        yield check_computegcmaptable, path

r_globallabel = re.compile(r"([\w]+)[:]")
r_expected = re.compile(r"\s*;;\s*expected\s*([(][-\d\s,+]+[)])")

def check_computegcmaptable(path):
    print
    print path.basename
    lines = path.readlines()
    tracker = FunctionGcRootTracker(lines)
    tracker.is_main = tracker.funcname == 'main'
    table = tracker.computegcmaptable(verbose=sys.maxint)
    tabledict = {}
    seen = {}
    for entry in table:
        print entry
        tabledict[entry[0]] = entry[1]
    # find the ";; expected" lines
    prevline = ""
    for line in lines:
        match = r_expected.match(line)
        if match:
            expected = eval(match.group(1))
            assert isinstance(expected, tuple)
            prevmatch = r_globallabel.match(prevline)
            assert prevmatch, "the computed table is not complete"
            label = prevmatch.group(1)
            assert label in tabledict
            got = tabledict[label]
            assert got == expected
            seen[label] = True
        prevline = line
    assert len(seen) == len(tabledict), (
        "computed table contains unexpected entries:\n%r" %
        [key for key in tabledict if key not in seen])
