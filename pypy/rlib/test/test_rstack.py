import py
import sys, dis
from pypy.rlib.rstack import Blackhole, resume_point
from pypy.rlib.rstack import find_basic_blocks, split_opcode_args
from pypy.rlib.rstack import find_resume_points_and_other_globals
from pypy.rlib.rstack import find_path_to_resume_point, ResumeData
from pypy.rlib.rstack import resume_state_create, resume_state_invoke
from pypy.rlib import rstack

def test_blackhole_simple():
    b = Blackhole()
    assert isinstance(b + b, Blackhole)
    assert isinstance(b.whatever, Blackhole)
    assert isinstance(b(b, b, 1), Blackhole)
    assert isinstance(b ** b, Blackhole)

def test_set_local_direct():
    try:
        def f(x):
            resume_data.set_local('x', 42)
            a = 1
            return x
        resume_data = ResumeData(None, "...", f)
        sys.settrace(resume_data.resume_tracer)
        res = f(1)
    finally:
        sys.settrace(None)
    assert res == 42

def test_set_local_direct_several():
    try:
        def f(x, y):
            resume_data.set_local('x', 42)
            resume_data.set_local('y', 42)
            return x + y
        resume_data = ResumeData(None, "...", f)
        sys.settrace(resume_data.resume_tracer)
        res = f(1, 1)
    finally:
        sys.settrace(None)
    assert res == 84

def test_set_local_nested():
    try:
        def f(x):
            g()
            return x
        def g():
            resume_data.set_local('x', 42, 1)
        resume_data = ResumeData(None, "...", f)
        sys.settrace(resume_data.resume_tracer)
        res = f(1)
    finally:
        sys.settrace(None)
    assert res == 42

def test_set_local_nested_several():
    try:
        def f(x, y):
            g()
            return x + y
        def g():
            resume_data.set_local('y', 22, 1)
            resume_data.set_local('x', 20, 1)
        resume_data = ResumeData(None, "...", f)
        sys.settrace(resume_data.resume_tracer)
        res = f(1, 1)
    finally:
        sys.settrace(None)
    assert res == 42


def test_resume_simple():
    def f(x):
        x += 1
        print 1, x
        resume_point("r1", x)
        print 2, x
        return x
    assert f(1) == 2
    s1 = resume_state_create(None, "r1", f, 1)
    r = resume_state_invoke(int, s1)
    assert r == 1

def test_resume_simple_module_attribute():
    def f(x):
        x += 1
        print 1, x
        rstack.resume_point("r1", x)
        print 2, x
        return x
    assert f(1) == 2
    s1 = resume_state_create(None, "r1", f, 1)
    r = resume_state_invoke(int, s1)
    assert r == 1

def test_normal_gettatr():
    def f(out):
        out.append(3)
        rstack.resume_point("r1", out)
        return out[-1]
    s1 = resume_state_create(None, "r1", f, [4])
    r = resume_state_invoke(int, s1)
    assert r == 4


def test_resume_many_args():
    def f(x, y, z):
        x += 1
        y += 2
        z += 3
        resume_point("r1", x, y, z)
        return x + y + z
    assert f(1, 2, 3) == 12
    s1 = resume_state_create(None, "r1", f, 1, 2, 3)
    res = resume_state_invoke(int, s1)
    assert res == 6

def test_several_resume_points():
    def f(x, y, z):
        x += 1
        y += 2
        resume_point("r1", x, y, returns=z)
        z += 3
        resume_point("r2", x, y, returns=z)
        return x + y + z
    assert f(1, 2, 3) == 12
    s1 = resume_state_create(None, "r1", f, 1, 2)
    res = resume_state_invoke(int, s1, returning=3)
    assert res == 9
    s2 = resume_state_create(None, "r2", f, 1, 2)
    res = resume_state_invoke(int, s2, returning=3)
    assert res == 6

def test_resume_in_branch():
    def f(cond, x):
        x += 1
        if cond:
            resume_point("r1", x)
            return x
        else:
            resume_point("r2", x)
            x += 1
            return x
    assert f(True, 1) == 2
    assert f(False, 2) == 4
    resume_data = resume_state_create(None, "r2", f, 2)
    res = resume_state_invoke(int, resume_data)
    assert res == 3
    resume_data = resume_state_create(None, "r1", f, 1)
    res = resume_state_invoke(int, resume_data)
    assert res == 1

def test_resume_branches_nested():
    def f(c1, c2, x):
        if c1:
            if c2:
                resume_point("r1", x)
                return x + 1
            else:
                resume_point("r2", x)
                return x + 2
        else:
            if c2:
                resume_point("r3", x)
                return x + 3
            else:
                resume_point("r4", x)
                return x + 4
    for i, name in enumerate("r1 r2 r3 r4".split()):
        s1 = resume_state_create(None, name, f, 2)
        res = resume_state_invoke(int, s1)
        assert res == 3 + i

def test_resume_while_simple():
    def f(x):
        a = 1
        result = 0
        while a <= x:
            resume_point("r", a, x, result)
            print result, a, x
            result += a
            a += 1
        return result
    s1 = resume_state_create(None, "r", f, 4, 6, 10)
    res = resume_state_invoke(int, s1)
    assert res == 25

def test_resume_while_non_unique():
    def f(x):
        a = 0
        result = 0
        while a <= x:
            resume_point("r", a, x, result)
            print result, a, x
            result += a
            a += 1
        return result
    s1 = resume_state_create(None, "r", f, 4, 6, 10)
    res = resume_state_invoke(int, s1)
    assert res == 25

def test_resume_function_call():
    def g(x):
        while 1:
            x += 1
        return x
    def f(x):
        x = g(x)
        resume_point("r", x)
        return x
    s1 = resume_state_create(None, "r", f, 1)
    res = resume_state_invoke(int, s1)
    assert res == 1

def forever(x):
    if x:
        while 1:
            print "bad idea!"
    return 41

def test_resume_global_function_call():
    old_forever = forever
    def f(x):
        forever(1)
        resume_point("r", x)
        x += forever(0)
        return x
    s1 = resume_state_create(None, "r", f, 1)
    res = resume_state_invoke(int, s1)
    assert res == 42
    assert forever is old_forever # make sure the globals were restored

def test_chained_states():
    def g(x, y):
        x += 1
        resume_point("rp1", x, y)
        return x + y
    def f(x, y, z):
        y += 1
        r = g(x, y)
        resume_point("rp2", z, returns=r)
        return r + z
    def example():
        v1 = f(1, 2, 3)
        s2 = resume_state_create(None, "rp2", f, 2)
        s1 = resume_state_create(s2, "rp1", g, 4, 5)
        return 100*v1 + resume_state_invoke(int, s1)
    res = example()
    assert res == 811

def test_resume_and_raise_and_catch():
    def g(x):
        x += 1
        resume_point("rp0", x)
        if x == 0:
            raise KeyError
        return x + 1
    def f(x):
        x = x - 1
        try:
            r = g(x)
            resume_point("rp1", returns=r)
        except KeyError:
            r = 42
        return r - 1
    def example():
        v1 = f(2)
        s1 = resume_state_create(None, "rp1", f)
        s0 = resume_state_create(s1, "rp0", g, 0)
        v2 = resume_state_invoke(int, s0)
        return v1*100 + v2
    res = example()
    assert res == 241

def DONOTtest_resume_in_except_block(): # probably not necessary 
    def g(x):
        if x:
            raise KeyError
    def f(x):
        x += 1
        try:
            g(x)
        except KeyError:
            resume_point("r1", x)
        return x
    s = resume_state_create(None, "r1", f, 42)
    res = resume_state_invoke(int, s)
    assert res == 42

def test_resume_in_finally_block():
    def g(x):
        x += 1
        resume_point("rp0", x)
        return x + 1
    def f(x):
        x = x - 1
        try:
            r = g(x)
            resume_point("rp1", returns=r)
        finally:
            r = 42 + r
        return r - 1
    def example():
        s1 = resume_state_create(None, "rp1", f)
        s0 = resume_state_create(s1, "rp0", g, 0)
        v2 = resume_state_invoke(int, s0)
        return v2
    res = example()
    assert res == 42


def test_jump_over_for():
    def f(x):
        result = 0
        for i in range(x):
            print "bad idea"
            result += i
        resume_point("r1", result)
        return result
    s = resume_state_create(None, "r1", f, 42)
    res = resume_state_invoke(int, s)
    assert res == 42

def test_resume_point_guarded_by_complex_condition():
    def f(x):
        x += 5
        if (x >> 8) & 0xff == 0:
            resume_point("r1", x)
        else:
            x += 8
        return x
    s = resume_state_create(None, "r1", f, 42)
    res = resume_state_invoke(int, s)
    assert res == 42
    
def test_function_with_bool():
    def f(x):
        x = bool(x)
        if x:
            resume_point("r1", x)
        else:
            x += 8
        return x
    dis.dis(f)
    s = resume_state_create(None, "r1", f, 42)
    res = resume_state_invoke(int, s)
    assert res == 42

def test_function_with_and():
    def f(x, y):
        if x and not y:
            resume_point("r1", x)
        else:
            x += 8
        return x
    s = resume_state_create(None, "r1", f, 42)
    res = resume_state_invoke(int, s)
    assert res == 42

def test_function_with_not():
    def f(x, y):
        x = not x
        if x:
            resume_point("r1", x)
        else:
            x += 8
        return x
    dis.dis(f)
    s = resume_state_create(None, "r1", f, 42)
    res = resume_state_invoke(int, s)
    assert res == 42

# _________________________________________________________________________
# test for bytecode analyzing functions

def test_find_basic_blocks():
    def f(cond, x):
        x += 1
        if cond:
            return x
        else:
            x += 1
            return x
    code = f.func_code.co_code
    res = find_basic_blocks(code)
    assert len(res) == 4

def test_split_opcode_args():
    def f(x):
        return x + 1
    dis.dis(f)
    res = split_opcode_args(f.func_code.co_code)
    assert len(res) == 4
    assert [op for pos, op, const in res] == [
        "LOAD_FAST", "LOAD_CONST", "BINARY_ADD", "RETURN_VALUE"]
    assert [pos for pos, op, const in res] == [0, 3, 6, 7]
    assert res[0][2] == 0 # LOAD_FAST
    assert res[1][2] == 1 # LOAD_CONST
    assert res[2][2] is None # BINARY_ADD
    assert res[3][2] is None # RETURN_VALUE

def test_find_resume_points():
    def f(cond, x):
        forever(x)
        x += 1
        if cond:
            resume_point("r1", x)
            return x
        else:
            resume_point("r2", x)
            x += 1
            return x
    rps, other_globals = find_resume_points_and_other_globals(f)
    assert len(rps) == 2
    assert rps[0][1] == "r1"
    assert rps[1][1] == "r2"
    assert not other_globals['resume_point']
    assert other_globals['forever']

def test_find_path_to_resume_point():
    def f(cond, x):
        x += 1
        if cond:
            resume_point("r1", x)
            return x
        else:
            resume_point("r2", x)
            x += 1
            return x
    paths, other_globals = find_path_to_resume_point(f)
    assert paths["r1"] == [("bool", True)]
    assert paths["r2"] == [("bool", False)]

def test_find_path_with_not():
    def f(x, y):
        y = not y
        resume_point("r2", x)
        if not not x:
            resume_point("r1", x)
        else:
            x += 8
        return x
    dis.dis(f)
    paths, other_globals = find_path_to_resume_point(f)
    assert paths["r1"][0][0] == "bool"
    assert paths["r1"][1] == ("bool", True)
    assert paths["r2"][0][0] == "bool"

