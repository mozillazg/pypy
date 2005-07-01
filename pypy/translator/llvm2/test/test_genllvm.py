from __future__ import division

import sys
import py

from pypy.translator.translator import Translator
from pypy.translator.llvm2.genllvm import genllvm
from pypy.translator.llvm2.test import llvmsnippet
from pypy.objspace.flow.model import Constant, Variable

from pypy.rpython.rtyper import RPythonTyper
from pypy.rpython.rarithmetic import r_uint

py.log.setconsumer("genllvm", py.log.STDOUT)
py.log.setconsumer("genllvm database prepare", None)


## def setup_module(mod):
##     mod.llvm_found = is_on_path("llvm-as")

def compile_function(function, annotate, view=False):
    t = Translator(function)
    a = t.annotate(annotate)
    t.specialize()
    a.simplify()
    return genllvm(t)


def test_return1():
    def simple1():
        return 1
    f = compile_function(simple1, [])
    assert f() == 1

def test_simple_branching():
    def simple5(b):
        if b:
            x = 12
        else:
            x = 13
        return x
    f = compile_function(simple5, [bool])
    assert f(True) == 12
    assert f(False) == 13

def test_int_ops():
    def ops(i):
        x = 0
        x += i < i
        x += i <= i
        x += i == i
        x += i != i
        x += i >= i
        x += i > i
        x += x % i
        #x += i is not None
        #x += i is None
        return i + 1 * i // i - 1
    f = compile_function(ops, [int])
    assert f(1) == 1
    assert f(2) == 2

def test_while_loop():
    def factorial(i):
        r = 1
        while i>1:
            r *= i
            i -= 1
        return r
    f = compile_function(factorial, [int])
    assert factorial(4) == 24
    assert factorial(5) == 120
    f = compile_function(factorial, [float])
    assert factorial(4.) == 24.
    assert factorial(5.) == 120.

def test_break_while_loop():
    def factorial(i):
        r = 1
        while 1:
            if i<=1:
                break
            r *= i
            i -= 1
        return r
    f = compile_function(factorial, [int])
    assert factorial(4) == 24
    assert factorial(5) == 120


def test_primitive_is_true():
    def var_is_true(v):
        return bool(v)
    f = compile_function(var_is_true, [int])
    assert f(256)
    assert not f(0)
    f = compile_function(var_is_true, [r_uint])
    assert f(r_uint(256))
    assert not f(r_uint(0))
    f = compile_function(var_is_true, [float])
    assert f(256.0)
    assert not f(0.0)


def test_uint_ops():
    def ops(i):
        x = r_uint(0)
        x += i < i
        x += i <= i
        x += i == i
        x += i != i
        x += i >= i
        x += i > i
        x += x % i
        #x += i is not None
        #x += i is None
        return i + 1 * i // i - 1
    f = compile_function(ops, [r_uint])
    assert f(1) == 1
    assert f(2) == 2

def test_float_ops():
    def ops(flt):
        x = 0
        x += flt < flt
        x += flt <= flt
        x += flt == flt
        x += flt != flt
        x += flt >= flt
        x += flt > flt
        #x += flt fs not None
        #x += flt is None
        return flt + 1 * flt / flt - 1
    f = compile_function(ops, [float])
    assert f(1) == 1
    assert f(2) == 2


def test_function_call():
    def callee():
        return 1
    def caller():
        return 3 + callee()
    f = compile_function(caller, [])
    assert f() == 4

def test_recursive_call():
    def call_ackermann(n, m):
        return ackermann(n, m)
    def ackermann(n, m):
        if n == 0:
            return m + 1
        if m == 0:
            return ackermann(n - 1, 1)
        return ackermann(n - 1, ackermann(n, m - 1))
    f = compile_function(call_ackermann, [int, int])
    assert f(0, 2) == 3
    
def test_tuple_getitem(): 
    def tuple_getitem(i): 
        l = (1,2,i)
        return l[1]
    f = compile_function(tuple_getitem, [int])
    assert f(1) == 2 

def test_nested_tuple():
    def nested_tuple(i): 
        l = (1,(1,2,i),i)
        return l[1][2]
    f = compile_function(nested_tuple, [int])
    assert f(4) == 4

def test_pbc_fns(): 
    def f2(x):
         return x+1
    def f3(x):
         return x+2
    def g(y):
        if y < 0:
            f = f2
        else:
            f = f3
        return f(y+3)
    f = compile_function(g, [int])
    assert f(-1) == 3
    assert f(0) == 5

def DONOT_test_simple_chars():
     def char_constant2(s):
         s = s + s + s
         return len(s + '.')
     def char_constant():
         return char_constant2("kk")    
     f = compile_function(char_constant, [])
     assert f() == 7

def DONOTtest_string_getitem():
    def string_test(i): 
        l = "Hello, World"
        return l[i]
    f = compile_function(string_test, [int])
    assert f(0) == ord("H")

class TestException(Exception):
    pass

def DONOTtest_exception():
    def raise_(i):
        if i:
            raise TestException()
        else:
            return 1
    def catch(i):
        try:
            return raise_(i)
        except TestException:
            return 0
    f = compile_function(catch, [int])
