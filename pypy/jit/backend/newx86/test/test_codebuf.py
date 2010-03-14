import py
import gc
from pypy.rpython.lltypesystem import rffi
from pypy.jit.backend.newx86.codebuf import CodeBufOverflow
from pypy.jit.backend.newx86.codebuf import CodeBufAllocator
from pypy.jit.backend.newx86.rx86 import R


class TestCodeBuilder:
    WORD = 4

    def setup_method(self, meth):
        CodeBufAllocator.alloc_count = 0
        self.cballoc = CodeBufAllocator(self.WORD)

    def teardown_method(self, meth):
        del self.cballoc
        for i in range(5):
            if CodeBufAllocator.alloc_count == 0:
                break
            gc.collect()
        else:
            raise AssertionError("alloc_count == %d" % (
                CodeBufAllocator.alloc_count,))

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

    def test_extract_subbuffer(self):
        c1 = self.cballoc.new_code_buffer(4096)
        c1.NOP()
        c2 = c1.extract_subbuffer(3)
        p1 = c1.get_current_position()
        assert p1[0] == chr(0x90)       # NOP
        p2 = c2.get_current_position()
        assert p2[4092] == chr(0x90)    # NOP
        assert not c2.is_full()
        c2.RET()
        c2.RET()
        c2.RET()
        p2 = c2.get_current_position()
        assert p2[0] == chr(0xC3)       # RET
        assert p2[1] == chr(0xC3)       # RET
        assert p2[2] == chr(0xC3)       # RET
        assert p2[4095] == chr(0x90)    # NOP
        assert c2.is_full()

    def test_extract_subbuffer_overflow(self):
        c = self.cballoc.new_code_buffer(4096)
        c.raise_on_overflow = True
        for i in range(4092):
            c.NOP()
        c1 = c.extract_subbuffer(3)
        c1.RET()
        c1.RET()
        c1.RET()
        c2 = c.extract_subbuffer(1)
        c2.PUSH_r(R.edx)
        p1 = c1.get_current_position()
        assert p1[0] == chr(0xC3)      # RET
        assert p1[1] == chr(0xC3)      # RET
        assert p1[2] == chr(0xC3)      # RET
        assert p1[3] == chr(0x52)      # PUSH edx
        assert p1[4] == chr(0x90)      # NOP
        assert p1[4095] == chr(0x90)   # NOP
        py.test.raises(CodeBufOverflow, c.extract_subbuffer, 1)
