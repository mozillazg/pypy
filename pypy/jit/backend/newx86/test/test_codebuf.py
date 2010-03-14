import py
import gc
from pypy.rpython.lltypesystem import rffi
from pypy.jit.backend.newx86.codebuf import CodeBufOverflow
from pypy.jit.backend.newx86.codebuf import CodeBufAllocator
from pypy.jit.backend.newx86.codebuf import AbstractCodeBuilder


class TestCodeBuilder:
    WORD = 4

    def setup_method(self, meth):
        CodeBufAllocator.alloc_count = 0
        self.cballoc = CodeBufAllocator(AbstractCodeBuilder)

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
        c.writechar('A')
        c.writechar('B')
        p1 = c.get_current_position()
        assert p1[0] == 'B'
        assert p1[1] == 'A'
        c.writechar('C')
        p2 = c.get_current_position()
        assert p2[0] == 'C'
        assert p2[1] == 'B'
        assert p2[2] == 'A'

    def test_overflowing(self):
        c = self.cballoc.new_code_buffer(4096)
        for i in range(4096):
            c.writechar('x')
        py.test.raises(CodeBufOverflow, c.writechar, 'x')

    def test_extract_subbuffer(self):
        c1 = self.cballoc.new_code_buffer(4096)
        c1.writechar('x')
        c2 = c1.extract_subbuffer(3, False)
        p1 = c1.get_current_position()
        assert p1[0] == 'x'
        p2 = c2.get_current_position()
        assert p2[4092] == 'x'
        assert not c2.is_full()
        c2.writechar('1')
        c2.writechar('2')
        c2.writechar('3')
        p2 = c2.get_current_position()
        assert p2[0] == '3'
        assert p2[1] == '2'
        assert p2[2] == '1'
        assert p2[4095] == 'x'
        assert c2.is_full()

    def test_extract_subbuffer_overflow(self):
        c = self.cballoc.new_code_buffer(4096)
        for i in range(4092):
            c.writechar('x')
        c1 = c.extract_subbuffer(3, False)
        c1.writechar('1')
        c1.writechar('2')
        c1.writechar('3')
        c2 = c.extract_subbuffer(1, False)
        c2.writechar('4')
        p1 = c1.get_current_position()
        assert p1[0] == '3'
        assert p1[1] == '2'
        assert p1[2] == '1'
        assert p1[3] == '4'
        assert p1[4] == 'x'
        assert p1[4095] == 'x'
        py.test.raises(CodeBufOverflow, c.extract_subbuffer, 1, False)

    def test_empty_code_buffer(self):
        c = self.cballoc.empty_code_buffer()
        py.test.raises(CodeBufOverflow, c.writechar, 'x')
