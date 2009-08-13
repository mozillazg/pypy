from pypy.lang.io.parserhack import parse, interpret
from pypy.lang.io.model import W_Object
from pypy.lang.io.coroutinemodel import W_Coroutine

import py

def test_isCurrent():
    inp = """Coroutine currentCoroutine isCurrent"""
    result, space = interpret(inp)
    assert result is space.w_true
    
def test_setRunMessage():
    inp = """m := message(1023)
    c := Coroutine currentCoroutine
    c setRunMessage(getSlot("m"))
    """
    res, space = interpret(inp)
    assert isinstance(res, W_Coroutine)
    assert res.slots['runMessage'] is space.w_lobby.slots['m']
    
def test_run():
    inp = """a := 12
    c := Coroutine currentCoroutine
    c setRunMessage(message(a := a + 1))
    c run
    """
    res, space = interpret(inp)
    assert isinstance(res, W_Coroutine)
    assert res.slots['result'].value == 13
    assert space.w_lobby.slots['a'].value == 12

def test_result_slot_proto():
    inp = """Coroutine result"""
    res, space = interpret(inp)
    assert res == space.w_nil
    
def test_set_result():
    inp = """
    c := Coroutine currentCoroutine clone
    c setResult(99)"""
    res, space = interpret(inp)
    print res.slots
    assert isinstance(res, W_Coroutine)
    assert res.slots['result'].value == 99
    
def test_parentCoroutine_proto():
    inp = 'Coroutine parentCoroutine'
    res, space = interpret(inp)
    assert res is space.w_nil
    
def test_parentCoroutine():
    inp = """
    Object try(Lobby foo := Coroutine currentCoroutine)
    foo parentCoroutine
    """
    res, space = interpret(inp)
    assert isinstance(res, W_Coroutine)
    assert res is space.w_lobby.slots['foo'].slots['parentCoroutine']
    
def test_coro_resume():
    py.test.skip()
    inp = """
    b := message(Coroutine currentCoroutine setResult(23); Coroutine currentCoroutine parentCoroutine resume; "bye" print)
    a := Coroutine currentCoroutine clone
    a setRunMessage(b) run
    a result
    """
    res,space = interpret(inp)
    assert res.value == 23
    
def test_coro_stacksize():
    inp = 'Coroutine clone stackSize'
    res, space = interpret(inp)
    assert res.value == 128000*10
    
def test_coro_clone():
    inp = 'Coroutine clone'
    res, space = interpret(inp)
    assert isinstance(res, W_Coroutine)
    
def test_scheduler_current_coro():
    inp = """list(Scheduler currentCoroutine, Coroutine currentCoroutine)"""
    res, space = interpret(inp)
    assert res.items[0] is res.items[1]
    
def test_coroutine_corofor():
    inp = """
    a := 4 clone
    a coroFor(message(99))"""
    res, space = interpret(inp)
    assert isinstance(res, W_Coroutine)
    assert res.slots['runTarget'] is space.w_lobby
    assert res.slots['runLocals'] is space.w_lobby
    