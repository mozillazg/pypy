
from pypy.jit.backend.x86.runner import CPU
from pypy.jit.backend.x86.test.test_regalloc import BaseTestRegalloc

class TestRecompilation(BaseTestRegalloc):
    def test_compile_bridge_not_deeper(self):
        ops = '''
        [i0]
        i1 = int_add(i0, 1)
        i2 = int_lt(i1, 20)
        guard_true(i2)
           fail(i1)
        jump(i1)
        '''
        loop = self.interpret(ops, [0])
        assert self.getint(0) == 20
        ops = '''
        [i1]
        i3 = int_add(i1, 1)
        fail(i3)
        '''
        bridge = self.attach_bridge(ops, loop, loop.operations[-2])
        self.cpu.set_future_value_int(0, 0)
        op = self.cpu.execute_operations(loop)
        assert op is bridge.operations[-1]
        assert self.getint(0) == 21
    
    def test_compile_bridge_deeper(self):
        ops = '''
        [i0]
        i1 = int_add(i0, 1)
        i2 = int_lt(i1, 20)
        guard_true(i2)
           fail(i1)
        jump(i1)
        '''
        loop = self.interpret(ops, [0])
        assert self.getint(0) == 20
        ops = '''
        [i1]
        i3 = int_add(i1, 1)
        i4 = int_add(i3, 1)
        i5 = int_add(i4, 1)
        i6 = int_add(i5, 1)
        fail(i3, i4, i5, i6)
        '''
        bridge = self.attach_bridge(ops, loop, loop.operations[-2])
        self.cpu.set_future_value_int(0, 0)
        op = self.cpu.execute_operations(loop)
        assert op is bridge.operations[-1]
        assert self.getint(0) == 21
        assert self.getint(1) == 22
        assert self.getint(2) == 23
        assert self.getint(3) == 24

#    def test_bridge_jump_to_other_loop(self):
#        xxx
