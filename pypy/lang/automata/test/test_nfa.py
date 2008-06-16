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

def test_nfa_build():
    re = compile_regex("abcd")
    assert re.transitions == {(0, "a"):[1],
                              (1, "b"):[2],
                              (2, "c"):[3],
                              (3, "d"):[4]}
    assert re.final_states.keys() == [4]
    re = compile_regex("ab|de")
    assert re.transitions == {(0, "a"):[1],
                              (1, "b"):[2],
                              (0, "d"):[3],
                              (3, "e"):[2]}
    assert re.final_states.keys() == [2]
    re = compile_regex("a(b|c)(d)")
    assert re.transitions == {(0, "a"):[1],
                              (1, "b"):[2],
                              (1, "c"):[2],
                              (2, "d"):[3]}
    assert re.final_states.keys() == [3]
    re = compile_regex("(a|c)(c|d)|ab")
    assert re.transitions == {(0, "a"):[1,3],
                              (0, "c"):[1],
                              (1, "c"):[2],
                              (1, "d"):[2],
                              (3, "b"):[2]}
    assert re.final_states.keys() == [2]
    re = compile_regex("a*")
    assert re.transitions == {(0, "a"):[0]}
    assert re.final_states.keys() == [0]

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
    
