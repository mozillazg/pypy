
from pypy.objspace.std.objspace import *
from pypy.interpreter import gateway
from pypy.objspace.std.dictobject import W_DictObject
from pypy.objspace.std.stringobject import W_StringObject

from pypy.rlib.objectmodel import r_dict

class W_WaryDictObject(W_DictObject):
    def __init__(w_self, space, wary_of=None, w_otherdict=None):
        from pypy.module.__builtin__.__init__ import BUILTIN_TO_INDEX
        W_DictObject.__init__(w_self, space, w_otherdict)
        if wary_of is None:
            wary_of = BUILTIN_TO_INDEX
        w_self.shadowed = [None] * len(wary_of)
        if w_otherdict:
            for key in wary_of:
                w_self.shadowed[wary_of[key]] = w_otherdict.get(space.wrap(key), None)
        w_self.wary_of = wary_of

registerimplementation(W_WaryDictObject)

def setitem__WaryDict_ANY_ANY(space, w_dict, w_key, w_newvalue):
    if space.is_true(space.isinstance(w_key, space.w_str)):
        s = space.str_w(w_key)
        i = w_dict.wary_of.get(s, -1)
        if i != -1:
            w_dict.shadowed[i] = w_newvalue
    w_dict.content[w_key] = w_newvalue

def delitem__WaryDict_ANY(space, w_dict, w_lookup):
    try:
        if space.is_true(space.isinstance(w_lookup, space.w_str)):
            s = space.str_w(w_lookup)
            i = w_dict.wary_of.get(s, -1)
            if i != -1:
                w_dict.shadowed[i] = None
        del w_dict.content[w_lookup]
    except KeyError:
        raise OperationError(space.w_KeyError, w_lookup)

from pypy.objspace.std import dicttype
register_all(vars(), dicttype)
