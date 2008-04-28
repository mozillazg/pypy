from pypy.jit.rainbow.test.test_hotpath import HotPathTest

from pypy.jit.tl import tiny3_hotpath as tiny3
from pypy.jit.tl.targettiny3hotpath import MyHintAnnotatorPolicy


class TestTL(HotPathTest):

    def test_tl(self):
        def main(bytecode, arg1, arg2, arg3):
            if bytecode == 0:
                bytecode = "{ #1 1 SUB ->#1 #1 }"
            elif bytecode == 1:
                bytecode = "{ 1.2 ->#2 1.3 ->#3 #1 1 SUB ->#1 #1 } #1 #2 #3"
            else:
                assert 0
            bytecode = [s for s in bytecode.split(' ') if s != '']
            args = [tiny3.IntBox(arg1), tiny3.IntBox(arg2), tiny3.IntBox(arg3)]
            return tiny3.repr(tiny3.interpret(bytecode, args))

        res = self.run(main, [1, 5, 0, 0], threshold=2,
                       policy=MyHintAnnotatorPolicy())
        assert "".join(res.chars._obj.items) == "0 1.200000 1.300000"
