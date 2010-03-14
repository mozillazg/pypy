import py
import gc
from pypy.jit.backend.newx86.codebuf import CodeBufOverflow
from pypy.jit.backend.newx86.codebuf import CodeBufAllocator
from pypy.jit.backend.newx86.rx86 import R


class TestCodeBuilder:
    WORD = 4

    def setup_method(self, meth):
        self.cballoc = CodeBufAllocator(self.WORD)

    def teardown_method(self, meth):
        for i in range(5):
            if self.cballoc.alloc_count == 0:
                break
            gc.collect()
        else:
            raise AssertionError("alloc_count == %d" % (
                self.cballoc.alloc_count,))

    def test_alloc_free(self):
        c1 = self.cballoc.new_code_buffer(4096)
        c2 = self.cballoc.new_code_buffer(8192)

    def test_writing_from_end(self):
        c = self.cballoc.new_code_buffer(4096)
        c.RET()
        c.NOP()
        p1 = c.get_current_position()
        assert p1[0] == chr(0x90)    # NOP
        assert p1[1] == chr(0xC3)    # RET
        c.PUSH_r(R.ecx)
        p2 = c.get_current_position()
        assert p2[0] == chr(0x51)    # PUSH ecx
        assert p2[1] == chr(0x90)    # NOP
        assert p2[2] == chr(0xC3)    # RET

    def test_overflowing(self):
        c = self.cballoc.new_code_buffer(4096)
        c.raise_on_overflow = True
        for i in range(4096):
            c.NOP()
        py.test.raises(CodeBufOverflow, c.NOP)
