from pypy.rlib.objectmodel import we_are_translated
from pypy.rlib.rmmap import PTR, alloc, free
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.jit.backend.newx86.rx86 import X86_32_CodeBuilder, X86_64_CodeBuilder


class CodeBufAllocator(object):
    def __init__(self, word):
        self.all_data_parts = []    # only if we are not translated
        self.alloc_count = 0
        self.cb_class = code_builder_cls[word]

    def __del__(self):
        for data, size in self.all_data_parts:
            free(data, size)
            self.alloc_count -= 1

    def new_code_buffer(self, map_size):
        data = alloc(map_size)
        if not we_are_translated():
            self.all_data_parts.append((data, map_size))
        return self.cb_class(data, map_size)


class CodeBufOverflow(Exception):
    "Raised when a code buffer is full."


class CodeBuilder(object):
    _mixin_ = True
    raise_on_overflow = False

    def __init__(self, data, map_size):
        self.data = data
        self.write_ofs = map_size

    def writechar(self, char):
        ofs = self.write_ofs - 1
        if ofs < 0:
            self._overflow_detected()
        self.data[ofs] = char
        self.write_ofs = ofs

    def _overflow_detected(self):
        assert self.raise_on_overflow
        raise CodeBufOverflow
    _overflow_detected._dont_inline_ = True

    def get_current_position(self):
        return rffi.ptradd(self.data, self.write_ofs)


class CodeBuilder32(CodeBuilder, X86_32_CodeBuilder):
    pass

class CodeBuilder64(CodeBuilder, X86_64_CodeBuilder):
    pass

code_builder_cls = {4: CodeBuilder32,
                    8: CodeBuilder64}
