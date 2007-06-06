import py
from pypy.lang.prolog.interpreter.interpreter import Rule
from pypy.lang.prolog.interpreter.parsing import get_engine, get_query_and_vars

def test_simple():
    e = get_engine("")
    head, body = get_query_and_vars("f(X) :- X = a.")[0].args
    r = Rule(head, body, e)
    query = get_query_and_vars("f(a).")[0]
    frame = r.make_frame(query)
    assert frame.localvarcache[0].dereference(e.heap).name == "a"
    cont = object()
    res = frame.run(frame.code.opcode, 0, cont)
    where, _, c2, _ = res
    assert cont is c2


