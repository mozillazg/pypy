from pypy.lang.prolog.interpreter.compiler import compile
from pypy.lang.prolog.interpreter.term import Atom, Var, Term, Number
from pypy.lang.prolog.interpreter.parsing import get_engine, get_query_and_vars

def test_simple():
    e = get_engine("")
    foo = Atom("foo")
    code = compile(foo, None, e)
    assert not code.opcode
    assert code.opcode_head == "c\x00\x00"
    assert code.constants == [foo]
    assert not code.can_contain_cut

def test_simple_withbody():
    e = get_engine("")
    foo = Atom("foo")
    bar = Atom("bar")
    code = compile(foo, bar, e)
    assert code.opcode_head == "c\x00\x00"
    assert code.opcode == "c\x00\x01s\x00\x00"
    assert code.constants == [foo, bar]
    assert not code.can_contain_cut

def test_simple_withargs():
    e = get_engine("")
    head, body = get_query_and_vars("f(X) :- g(X).")[0].args
    code = compile(head, body, e)
    assert code.opcode_head == "m\x00\x00t\x00\x00"
    assert code.opcode == "a\x00\x00l\x00\x00t\x00\x01s\x00\x00"
    assert code.constants == []
    assert code.term_info == [("f", 1, "f/1"), ("g", 1, "g/1")]
    assert not code.can_contain_cut

def test_simple_and():
    e = get_engine("")
    head, body = get_query_and_vars("f(X, Y) :- g(X), h(Y).")[0].args
    code = compile(head, body, e)
    assert code.opcode_head == "m\x00\x00m\x00\x01t\x00\x00"
    assert code.opcode == "a\x00\x00a\x00\x01l\x00\x00t\x00\x01s\x00\x00l\x00\x01t\x00\x02s\x00\x01"
    assert code.constants == []
    assert code.term_info == [("f", 2, "f/2"), ("g", 1, "g/1"), ("h", 1, "h/1")]
    assert not code.can_contain_cut

def test_nested_term():
    e = get_engine("")
    head = get_query_and_vars("f(g(X), a).")[0]
    code = compile(head, None, e)
    assert code.opcode_head == "m\x00\x00t\x00\x00c\x00\x00t\x00\x01"
    assert code.term_info == [("g", 1, "g/1"), ("f", 2, "f/2")]
    assert code.constants == [Atom("a")]
    assert not code.can_contain_cut

def test_unify():
    e = get_engine("")
    head, body = get_query_and_vars("f(X, Y) :- g(X) = g(Y).")[0].args
    code = compile(head, body, e)
    assert code.opcode_head == "m\x00\x00m\x00\x01t\x00\x00"
    assert code.opcode == "a\x00\x00a\x00\x01l\x00\x00t\x00\x01l\x00\x01t\x00\x01U"
    assert code.constants == []
    assert code.term_info == [("f", 2, "f/2"), ("g", 1, "g/1")]
    assert not code.can_contain_cut

def test_dynamic_call():
    e = get_engine("")
    head, body = get_query_and_vars("f(X, Y) :- X, call(Y).")[0].args
    code = compile(head, body, e)
    assert code.opcode_head == "m\x00\x00m\x00\x01t\x00\x00"
    assert code.opcode.startswith("a\x00\x00a\x00\x01l\x00\x00Dl\x00\x01t\x00\x01b")
    assert code.term_info == [("f", 2, "f/2"), ("call", 1, "call/1")]
    assert code.can_contain_cut

def test_cut():
    e = get_engine("")
    head, body = get_query_and_vars("f(X, Y) :- !.")[0].args
    code = compile(head, body, e)
    assert code.opcode_head == "m\x00\x00m\x00\x01t\x00\x00"
    assert code.opcode == "a\x00\x00a\x00\x01C"
    assert code.term_info == [("f", 2, "f/2")]
    assert code.can_contain_cut

def test_arithmetic():
    # XXX compile is
    e = get_engine("")
    head, body = get_query_and_vars("f(X) :- Y is X - 1, f(Y).")[0].args
    code = compile(head, body, e)
    assert code.opcode_head == "m\x00\x00t\x00\x00"
    assert code.opcode.startswith(
        "a\x00\x00m\x00\x01l\x00\x00c\x00\x00t\x00\x01t\x00\x02b\x00\x02"
        "a\x00\x01")
    assert code.constants == [Number(1)]
    assert code.term_info == [("f", 1, "f/1"), ("-", 2, "-/2"),
                              ("is", 2, "is/2")]
    assert not code.can_contain_cut
 
