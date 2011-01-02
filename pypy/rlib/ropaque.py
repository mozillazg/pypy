
""" ROpaque is a way of shoveling high-level RPython objects (just instances)
via low-level type interface. This works easily when translated and creates
a special type when untranslated
"""

from pypy.rpython.lltypesystem import lltype
from pypy.rpython.annlowlevel import cast_instance_to_base_ptr,\
     cast_base_ptr_to_instance
from pypy.rpython.lltypesystem.rclass import OBJECTPTR
from pypy.rlib.objectmodel import we_are_translated, specialize

ROPAQUE = lltype.Ptr(lltype.GcOpaqueType('ropaque'))

def cast_obj_to_ropaque(obj):
    if not we_are_translated():
        res = lltype.opaqueptr(ROPAQUE.TO, 'ropaque', _obj=obj)
        obj._ropaqu_ptr = res # XXX ugly hack for weakrefs
        return res
    else:
        ptr = cast_instance_to_base_ptr(obj)
        return lltype.cast_opaque_ptr(ROPAQUE, ptr)

@specialize.arg(0)
def cast_ropaque_to_obj(Class, ropaque):
    if not we_are_translated():
        return ropaque._obj._obj
    else:
        ptr = lltype.cast_opaque_ptr(OBJECTPTR, ropaque)
        return cast_base_ptr_to_instance(Class, ptr)
