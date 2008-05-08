
from pypy.rpython.rbuilder import AbstractStringBuilderRepr
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.lltypesystem.rstr import STR
from pypy.rpython.annlowlevel import llstr
from pypy.rlib import rgc

STRINGBUILDER = lltype.GcStruct('stringbuilder',
                              ('allocated', lltype.Signed),
                              ('used', lltype.Signed),
                              ('buf', lltype.Ptr(STR)))

class StringBuilderRepr(AbstractStringBuilderRepr):
    lowleveltype = lltype.Ptr(STRINGBUILDER)

    @staticmethod
    def ll_new(init_size):
        ll_builder = lltype.malloc(STRINGBUILDER)
        ll_builder.allocated = init_size
        ll_builder.used = 0
        ll_builder.buf = rgc.resizable_buffer_of_shape(STR, init_size)
        return ll_builder

    @staticmethod
    def ll_append(ll_builder, str):
        ll_str = llstr(str)
        used = ll_builder.used
        lgt = len(ll_str.chars)
        allocated = ll_builder.allocated
        needed = lgt + used
        if needed >= allocated:
            # XXX tune overallocation scheme
            new_allocated = needed + 100
            ll_builder.buf = rgc.resize_buffer(ll_builder.buf, used,
                                               new_allocated)
            ll_builder.allocated = new_allocated
        ll_str.copy_contents(ll_str, ll_builder.buf, 0, used, lgt)
        ll_builder.used = used + lgt
    
    @staticmethod
    def ll_append_char(ll_builder, char):
        if ll_builder.used == ll_builder.allocated:
            # XXX tune overallocation scheme
            new_allocated = ll_builder.allocated + 100
            ll_builder.buf = rgc.resize_buffer(ll_builder.buf, ll_builder.used,
                                               new_allocated)
            ll_builder.allocated = new_allocated
        ll_builder.buf.chars[ll_builder.used] = char
        ll_builder.used += 1

    @staticmethod
    def ll_build(ll_builder):
        final_size = ll_builder.used
        return rgc.finish_building_buffer(ll_builder.buf, final_size)

stringbuilder_repr = StringBuilderRepr()
