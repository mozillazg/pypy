from pypy.rlib.objectmodel import we_are_translated
from pypy.rlib.rmmap import PTR, alloc, free
from pypy.rpython.lltypesystem import lltype, rffi


class CodeBufAllocator(object):
    alloc_count = 0

    def __init__(self, cb_class):
        self.all_data_parts = []    # only if we are not translated
        self.cb_class = cb_class

    def __del__(self):
        if not we_are_translated():
            for data, size in self.all_data_parts:
                free(data, size)
                CodeBufAllocator.alloc_count -= 1

    def new_code_buffer(self, map_size):
        data = alloc(map_size)
        if not we_are_translated():
            CodeBufAllocator.alloc_count += 1
            self.all_data_parts.append((data, map_size))
        return self.cb_class(data, map_size, True)

    def empty_code_buffer(self):
        return self.cb_class(lltype.nullptr(PTR.TO), 0, True)


class CodeBufOverflow(Exception):
    "Raised when a code buffer is full."


class AbstractCodeBuilder(object):
    _mixin_ = True

    def __init__(self, data, map_size, raise_on_overflow):
        self.data = data
        self.write_ofs = map_size
        self.raise_on_overflow = raise_on_overflow

    def writechar(self, char):
        """Writes a character at the *end* of buffer, and decrement the
        current position.
        """
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
        """Return the current position.  Note that this starts at the end."""
        return rffi.ptradd(self.data, self.write_ofs)

    def extract_subbuffer(self, subsize, raise_on_overflow):
        subbuf = self.data
        if self.write_ofs < subsize:
            self._overflow_detected()
        self.write_ofs -= subsize
        self.data = rffi.ptradd(self.data, subsize)
        return self.__class__(subbuf, subsize, raise_on_overflow)

    def is_full(self):
        return self.write_ofs == 0
