import py
from pypy.jit.tl.tlopcode import compile, NEW
from pypy.jit.tl.test import test_tl
from pypy.jit.tl.tlc import ConstantPool
    
def test_constant_pool():
    pool = ConstantPool()
    bytecode = compile("""
        NEW foo,bar
    """, pool)
    expected = test_tl.list2bytecode([NEW, 0])
    assert expected == bytecode
    assert pool.strlists == [['foo', 'bar']]

class TestTLC(test_tl.TestTL):
    @staticmethod
    def interp(code='', pc=0, inputarg=0):
        from pypy.jit.tl.tlc import interp
        return interp(code, pc, inputarg)
 
    def test_basic_cons_cell(self):
        bytecode = compile("""
            NIL
            PUSHARG
            CONS
            PUSH 1
            CONS
            CDR
            CAR
        """)

        res = self.interp(bytecode, 0, 42)
        assert res == 42

    def test_nth(self):
        bytecode = compile("""
            NIL
            PUSH 4
            CONS
            PUSH 2
            CONS
            PUSH 1
            CONS
            PUSHARG
            DIV
        """)

        res = self.interp(bytecode, 0, 0)
        assert res == 1
        res = self.interp(bytecode, 0, 1)
        assert res == 2
        res = self.interp(bytecode, 0, 2)
        assert res == 4

        py.test.raises(IndexError, self.interp, bytecode, 0, 3)
            
    def test_concat(self):
        bytecode = compile("""
            NIL
            PUSH 4
            CONS
            PUSH 2
            CONS
            NIL
            PUSH 5
            CONS
            PUSH 3
            CONS
            PUSH 1
            CONS
            ADD
            PUSHARG
            DIV
        """)

        for i, n in enumerate([2, 4, 1, 3, 5]):
            res = self.interp(bytecode, 0, i)
            assert res == n

    def test_concat_errors(self):
        bytecode = compile("""
            NIL
            PUSH 4
            ADD
        """)
        py.test.raises(TypeError, self.interp, bytecode, 0, 0)

        bytecode = compile("""
            PUSH 4
            NIL
            ADD
        """)
        py.test.raises(TypeError, self.interp, bytecode, 0, 0)


        bytecode = compile("""
            NIL
            PUSH 1
            CONS
            PUSH 4
            ADD
        """)
        py.test.raises(TypeError, self.interp, bytecode, 0, 0)

        bytecode = compile("""
            PUSH 4
            NIL
            PUSH 1
            CONS
            ADD
        """)
        py.test.raises(TypeError, self.interp, bytecode, 0, 0)


        bytecode = compile("""
            PUSH 2
            PUSH 1
            CONS
            NIL
            ADD
        """)
        py.test.raises(TypeError, self.interp, bytecode, 0, 0)

    def test_new_obj(self):
        from pypy.jit.tl.tlc import interp_eval, InstanceObj
        pool = ConstantPool()
        bytecode = compile("""
            NEW foo,bar
        """, pool)
        obj = interp_eval(bytecode, 0, None, pool)
        assert isinstance(obj, InstanceObj)
        assert len(obj.values) == 2
        assert sorted(obj.cls.attributes.keys()) == ['bar', 'foo']

    def test_setattr(self):
        from pypy.jit.tl.tlc import interp_eval, nil
        pool = ConstantPool()
        bytecode = compile("""
            NEW foo,bar
            PICK 0
            PUSH 42
            SETATTR foo,
        """, pool)
        obj = interp_eval(bytecode, 0, None, pool)
        assert obj.values[0].int_o() == 42
        assert obj.values[1] is nil

    def test_getattr(self):
        from pypy.jit.tl.tlc import interp_eval, nil
        pool = ConstantPool()
        bytecode = compile("""
            NEW foo,bar
            PICK 0
            PUSH 42
            SETATTR bar,
            GETATTR bar,
        """, pool)
        res = interp_eval(bytecode, 0, nil, pool)
        assert res.int_o() == 42

    def test_obj_truth(self):
        from pypy.jit.tl.tlc import interp_eval, nil
        pool = ConstantPool()
        bytecode = compile("""
            NEW foo,bar
            BR_COND true
            PUSH 12
            PUSH 1
            BR_COND exit
        true:
            PUSH 42
        exit:
            RETURN
        """, pool)
        res = interp_eval(bytecode, 0, nil, pool)
        assert res.int_o() == 42

    def test_obj_equality(self):
        from pypy.jit.tl.tlc import interp_eval, nil
        pool = ConstantPool()
        bytecode = compile("""
            NEW foo,bar
            NEW foo,bar
            EQ
        """, pool)
        res = interp_eval(bytecode, 0, nil, pool)
        assert res.int_o() == 0
