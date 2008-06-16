import py
from pypy import conftest

from pypy.rpython.test.test_llinterp import interpret

from pypy.lang.automata.nfa import *

def rundfa():
    a = getautomaton()
    assert 'a' in a.get_language()
    assert 'b' in a.get_language()
    assert 'c' in a.get_language()
    assert 'd' not in a.get_language()

    assert recognize(a, "aaaaaaaaaab")
    assert recognize(a, "b")
    assert recognize(a, "aaaacb")
    
    assert not recognize(a, "a")
    assert not recognize(a, "xyza")

    assert recognize(a, "acccb")

def test_nfa_simple():
    rundfa()

def test_nfa_interp():
    interpret(rundfa, [])

def test_nfa_compiledummy():
    py.test.skip("not working")
    def main(gets):
        a = getautomaton()
        dfatable, final_states = convertdfa(a)
        s = ["aaaaaaaaaab", "aaaa"][gets]
        return recognizetable(dfatable, s, final_states)
    assert interpret(main, [0])
    assert not interpret(main, [1])

def test_nfa_compiledummy2():
    py.test.skip("not working")
    def main(gets):
        a = getautomaton()
        alltrans, final_states = convertagain(a)
        s = ["aaaaaaaaaab", "aaaa"][gets]
        return recognizeparts(alltrans, final_states, s)
    assert interpret(main, [0])
    assert not interpret(main, [1])
    
