from rpython.rlib import jit
from rpython.rlib.objectmodel import specialize
from rpython.rlib.rstring import StringBuilder
from rpython.rlib.rstruct.error import StructError
from rpython.rlib.rstruct.formatiterator import FormatIterator
from rpython.rlib.rstruct.standardfmttable import standard_fmttable
from rpython.rlib.unroll import unrolling_iterable
from rpython.rtyper.lltypesystem import rffi

from pypy.interpreter.error import OperationError, oefmt
from pypy.interpreter.utf8 import utf8ord, utf8chr

wchar_len = rffi.sizeof(rffi.WCHAR_T)

unroll_pack_unichar_iter = unrolling_iterable(range(wchar_len-1, -1, -1))
def pack_unichar(fmtiter):
    value = utf8ord(fmtiter.accept_unicode_arg())

    # TODO: What do I do on a system with sizeof(wchar_t) == 2? I can't
    #       split it reasonably?
    #if not min <= value <= max:
    #    raise StructError(errormsg)

    if fmtiter.bigendian:
        for i in unroll_pack_unichar_iter:
            x = (value >> (8*i)) & 0xff
            fmtiter.result.append(chr(x))
    else:
        for i in unroll_pack_unichar_iter:
            fmtiter.result.append(chr(value & 0xff))
            value >>= 8

unroll_upack_unichar_iter = unrolling_iterable(range(wchar_len))
def unpack_unichar(fmtiter):
    #intvalue = inttype(0)
    intvalue = 0
    s = fmtiter.read(wchar_len)
    idx = 0
    if fmtiter.bigendian:
        for i in unroll_upack_unichar_iter:
            x = ord(s[idx])
            intvalue <<= 8
            #intvalue |= inttype(x)
            intvalue |= x
            idx += 1
    else:
        for i in unroll_upack_unichar_iter:
            x = ord(s[idx])
            #intvalue |= inttype(x) << (8*i)
            intvalue |= x << (8*i)
            idx += 1

    try:
        value = utf8chr(intvalue)
    except ValueError:
        raise oefmt(fmtiter.space.w_ValueError,
                    'character U+%s is not in range[U+0000; '
                     'U+10ffff]', hex(intvalue))
    fmtiter.appendobj(value)

class PackFormatIterator(FormatIterator):
    def __init__(self, space, args_w, size):
        self.space = space
        self.args_w = args_w
        self.args_index = 0
        self.result = StringBuilder(size)

    # This *should* be always unroll safe, the only way to get here is by
    # unroll the interpret function, which means the fmt is const, and thus
    # this should be const (in theory ;)
    @jit.unroll_safe
    @specialize.arg(1)
    def operate(self, fmtdesc, repetitions):
        pack = fmtdesc.pack
        if fmtdesc.fmtchar == 'u':
            pack = pack_unichar

        if fmtdesc.needcount:
            pack(self, repetitions)
        else:
            for i in range(repetitions):
                pack(self)
    _operate_is_specialized_ = True

    @jit.unroll_safe
    def align(self, mask):
        pad = (-self.result.getlength()) & mask
        self.result.append_multiple_char('\x00', pad)

    def finished(self):
        if self.args_index != len(self.args_w):
            raise StructError("too many arguments for struct format")

    def accept_obj_arg(self):
        try:
            w_obj = self.args_w[self.args_index]
        except IndexError:
            raise StructError("struct format requires more arguments")
        self.args_index += 1
        return w_obj

    def accept_int_arg(self):
        return self._accept_integral("int_w")

    def accept_uint_arg(self):
        return self._accept_integral("uint_w")

    def accept_longlong_arg(self):
        return self._accept_integral("r_longlong_w")

    def accept_ulonglong_arg(self):
        return self._accept_integral("r_ulonglong_w")

    @specialize.arg(1)
    def _accept_integral(self, meth):
        space = self.space
        w_obj = self.accept_obj_arg()
        if (space.isinstance_w(w_obj, space.w_int) or
            space.isinstance_w(w_obj, space.w_long)):
            w_index = w_obj
        else:
            w_index = None
            w_index_method = space.lookup(w_obj, "__index__")
            if w_index_method is not None:
                try:
                    w_index = space.index(w_obj)
                except OperationError, e:
                    if not e.match(space, space.w_TypeError):
                        raise
                    pass
            if w_index is None:
                w_index = self._maybe_float(w_obj)
        return getattr(space, meth)(w_index)

    def _maybe_float(self, w_obj):
        space = self.space
        if space.isinstance_w(w_obj, space.w_float):
            msg = "struct: integer argument expected, got float"
        else:
            msg = "integer argument expected, got non-integer"
        space.warn(space.wrap(msg), space.w_DeprecationWarning)
        return space.int(w_obj)   # wrapped float -> wrapped int or long

    def accept_bool_arg(self):
        w_obj = self.accept_obj_arg()
        return self.space.is_true(w_obj)

    def accept_str_arg(self):
        w_obj = self.accept_obj_arg()
        return self.space.str_w(w_obj)

    def accept_unicode_arg(self):
        w_obj = self.accept_obj_arg()
        return self.space.unicode_w(w_obj)

    def accept_float_arg(self):
        w_obj = self.accept_obj_arg()
        return self.space.float_w(w_obj)


class UnpackFormatIterator(FormatIterator):
    def __init__(self, space, buf):
        self.space = space
        self.buf = buf
        self.length = buf.getlength()
        self.pos = 0
        self.result_w = []     # list of wrapped objects

    # See above comment on operate.
    @jit.unroll_safe
    @specialize.arg(1)
    def operate(self, fmtdesc, repetitions):
        unpack = fmtdesc.unpack
        if fmtdesc.fmtchar == 'u':
            unpack = unpack_unichar

        if fmtdesc.needcount:
            unpack(self, repetitions)
        else:
            for i in range(repetitions):
                unpack(self)
    _operate_is_specialized_ = True

    def align(self, mask):
        self.pos = (self.pos + mask) & ~mask

    def finished(self):
        if self.pos != self.length:
            raise StructError("unpack str size too long for format")

    def read(self, count):
        end = self.pos + count
        if end > self.length:
            raise StructError("unpack str size too short for format")
        s = self.buf.getslice(self.pos, end, 1, count)
        self.pos = end
        return s

    @specialize.argtype(1)
    def appendobj(self, value):
        self.result_w.append(self.space.wrap(value))
