from pypy.lang.io.parserhack import parse, interpret
from pypy.lang.io.model import W_Object
import py

def test_isCurrent():
    inp = """Coroutine currentCoroutine isCurrent"""
    result, space = interpret(inp)
    assert result is space.w_true
    
def test_coro_resume():
    py.test.skip()
    inp = """
    b := message(currentCoro setResult(23); currentCoro parentCoroutine resume; "bye" print)
    a := Coroutine currentCoroutine clone
    a setRunMessage(b) run
    a result
    """
    res,space = interpret(inp)
    assert res.value == 23
    
