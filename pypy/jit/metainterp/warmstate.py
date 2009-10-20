
from pypy.rpython.lltypesystem import lltype, llmemory, rstr
from pypy.rpython.ootypesystem import ootype
from pypy.rlib.objectmodel import specialize
from pypy.rlib.rarithmetic import intmask
from pypy.jit.metainterp import history

# ____________________________________________________________

@specialize.arg(0)
def unwrap(TYPE, box):
    if TYPE is lltype.Void:
        return None
    if isinstance(TYPE, lltype.Ptr):
        return box.getref(TYPE)
    if isinstance(TYPE, ootype.OOType):
        return box.getref(TYPE)
    if TYPE == lltype.Float:
        return box.getfloat()
    else:
        return lltype.cast_primitive(TYPE, box.getint())

@specialize.ll()
def wrap(cpu, value, in_const_box=False):
    if isinstance(lltype.typeOf(value), lltype.Ptr):
        if lltype.typeOf(value).TO._gckind == 'gc':
            value = lltype.cast_opaque_ptr(llmemory.GCREF, value)
            if in_const_box:
                return history.ConstPtr(value)
            else:
                return history.BoxPtr(value)
        else:
            adr = llmemory.cast_ptr_to_adr(value)
            value = cpu.cast_adr_to_int(adr)
            # fall through to the end of the function
    elif isinstance(lltype.typeOf(value), ootype.OOType):
        value = ootype.cast_to_object(value)
        if in_const_box:
            return history.ConstObj(value)
        else:
            return history.BoxObj(value)
    elif isinstance(value, float):
        if in_const_box:
            return history.ConstFloat(value)
        else:
            return history.BoxFloat(value)
    else:
        value = intmask(value)
    if in_const_box:
        return history.ConstInt(value)
    else:
        return history.BoxInt(value)

@specialize.arg(0)
def equal_whatever(TYPE, x, y):
    if isinstance(TYPE, lltype.Ptr):
        if TYPE.TO is rstr.STR or TYPE.TO is rstr.UNICODE:
            return rstr.LLHelpers.ll_streq(x, y)
    if TYPE is ootype.String or TYPE is ootype.Unicode:
        return x.ll_streq(y)
    return x == y

@specialize.arg(0)
def hash_whatever(TYPE, x):
    # Hash of lltype or ootype object.
    # Only supports strings, unicodes and regular instances,
    # as well as primitives that can meaningfully be cast to Signed.
    if isinstance(TYPE, lltype.Ptr):
        if TYPE.TO is rstr.STR or TYPE.TO is rstr.UNICODE:
            return rstr.LLHelpers.ll_strhash(x)    # assumed not null
        else:
            if x:
                return lltype.identityhash(x)
            else:
                return 0
    elif TYPE is ootype.String or TYPE is ootype.Unicode:
        return x.ll_hash()
    elif isinstance(TYPE, ootype.OOType):
        if x:
            return ootype.identityhash(x)
        else:
            return 0
    else:
        return lltype.cast_primitive(lltype.Signed, x)
