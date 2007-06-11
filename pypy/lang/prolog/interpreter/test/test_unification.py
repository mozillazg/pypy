import py
from pypy.lang.prolog.interpreter.error import UnificationFailed
from pypy.lang.prolog.interpreter.term import Atom, Var, Number, Term, BlackBox
from pypy.lang.prolog.interpreter.engine import Trail, Engine

def test_atom():
    a = Atom.newatom("hallo")
    b = Atom.newatom("hallo")
    # does not raise
    a.unify(b, None)
    py.test.raises(UnificationFailed, "a.unify(Atom.newatom('xxx'), None)")

def test_var():
    b = Var()
    trail = Trail()
    b.unify(Atom.newatom("hallo"), trail)
    assert b.getvalue(trail).name == "hallo"
    a = Var()
    b = Var()
    a.unify(b, trail)
    a.unify(Atom.newatom("hallo"), trail)
    assert a.getvalue(trail).name == "hallo"
    assert b.getvalue(trail).name == "hallo"

def test_unify_var():
    b = Var()
    trail = Trail()
    b.unify(b, trail)
    b.unify(Atom.newatom("hallo"), trail)
    py.test.raises(UnificationFailed, b.unify, Atom.newatom("bye"), trail)

def test_recursive():
    b = Var()
    trail = Trail()
    b.unify(Term("hallo", [b]), trail)

def test_term():
    X = Var()
    Y = Var()
    t1 = Term("f", [Atom.newatom("hallo"), X])
    t2 = Term("f", [Y, Atom.newatom("HALLO")])
    trail = Trail()
    print t1, t2
    t1.unify(t2, trail)
    assert X.getvalue(trail).name == "HALLO"
    assert Y.getvalue(trail).name == "hallo"

def test_blackbox():
    bl1 = BlackBox()
    bl2 = BlackBox()
    trail = Trail()
    bl1.unify(bl1, trail)
    py.test.raises(UnificationFailed, bl1.unify, bl2, trail)

def test_run():
    e = Engine()
    e.add_rule(Term("f", [Atom.newatom("a"), Atom.newatom("b")]))
    X = Var()
    Y = Var()
    e.add_rule(Term("f", [X, X]))
    e.add_rule(Term(":-", [Term("f", [X, Y]),
                           Term("f", [Y, X])]))
    X = e.trail.newvar()
    e.run(Term("f", [Atom.newatom("b"), X]))
    assert X.dereference(e.trail).name == "b"
    e.run(Term("f", [Atom.newatom("b"), Atom.newatom("a")]))
    e.run(Term("f", [Atom.newatom("c"), Atom.newatom("c")]))


