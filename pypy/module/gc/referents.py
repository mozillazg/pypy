from pypy.rlib import rgc
from pypy.interpreter.baseobjspace import W_Root, Wrappable
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.gateway import ObjSpace
from pypy.rlib.objectmodel import we_are_translated


class W_GcRef(Wrappable):
    def __init__(self, gcref):
        self.gcref = gcref

W_GcRef.typedef = TypeDef("GcRef")


def wrap(space, gcref):
    w_obj = rgc.try_cast_gcref_to_instance(W_Root, gcref)
    if w_obj is None:
        w_obj = space.wrap(W_GcRef(gcref))
    return w_obj

def unwrap(space, w_obj):
    gcrefobj = space.interpclass_w(w_obj)
    if isinstance(gcrefobj, W_GcRef):
        gcref = gcrefobj.gcref
    else:
        gcref = rgc.cast_instance_to_gcref(w_obj)
    return gcref

def get_rpy_objects(space):
    """Return a list of all objects (huge).
    This contains a lot of GcRefs."""
    result = rgc._get_objects()
    return space.newlist([wrap(space, gcref) for gcref in result])

def get_rpy_referents(space, w_obj):
    """Return a list of all the referents, as reported by the GC.
    This is likely to contain a lot of GcRefs."""
    gcref = unwrap(space, w_obj)
    lst = rgc._get_referents(gcref)
    return space.newlist([wrap(space, gcref) for gcref in lst])

def get_rpy_memory_usage(space, w_obj):
    """Return the memory usage of just the given object or GcRef.
    This does not include the internal structures of the object."""
    gcref = unwrap(space, w_obj)
    size = rgc._get_memory_usage(gcref)
    return space.wrap(size)

def get_objects(space):
    """Return a list of all app-level objects."""
    result = []
    for gcref in rgc._get_objects():
        w_obj = rgc.try_cast_gcref_to_instance(W_Root, gcref)
        if w_obj is not None:
            if we_are_translated() or hasattr(w_obj, 'typedef'):
                result.append(w_obj)
    return space.newlist(result)

def get_referents(space, args_w):
    """Return the list of objects that directly refer to any of objs.
    Approximative: follow references recursively until it finds
    app-level objects."""
    result = []
    pending = []
    for w_obj in args_w:
        pending.append(unwrap(space, w_obj))
    i = 0
    while i < len(pending):
        gcref = pending[i]
        i += 1
        lst = rgc._get_referents(gcref)
        for gcref in lst:
            w_subobj = rgc.try_cast_gcref_to_instance(W_Root, gcref)
            if w_subobj is not None:
                result.append(w_subobj)
            elif gcref not in pending:
                pending.append(gcref)
    return space.newlist(result)
get_referents.unwrap_spec = [ObjSpace, 'args_w']

def get_memory_usage(space, args_w):
    """Return the total size of the object(s) passed as argument.
    Approximative: follow references recursively and compute the
    total of the sizes, stopping at other app-level objects."""
    result = 0
    pending = []
    for w_obj in args_w:
        pending.append(unwrap(space, w_obj))
    i = 0
    while i < len(pending):
        gcref = pending[i]
        i += 1
        result += rgc._get_memory_usage(gcref)
        lst = rgc._get_referents(gcref)
        for gcref in lst:
            if (rgc.try_cast_gcref_to_instance(W_Root, gcref) is None
                and gcref not in pending):
                pending.append(gcref)
    return space.wrap(result)
get_memory_usage.unwrap_spec = [ObjSpace, 'args_w']
