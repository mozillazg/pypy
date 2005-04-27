from pypy.objspace.std.stdtypedef import *
from pypy.objspace.std.basestringtype import basestring_typedef
from pypy.interpreter.error import OperationError

from sys import maxint

unicode_capitalize = MultiMethod('capitalize', 1)
unicode_center     = MultiMethod('center', 2, )
unicode_count      = MultiMethod('count', 4, defaults=(0, maxint))      
unicode_encode     = MultiMethod('encode', 3, defaults=(None, None))
unicode_endswith   = MultiMethod('endswith', 2) #[optional arguments not supported now]
unicode_expandtabs = MultiMethod('expandtabs', 2, defaults=(8,))
unicode_find       = MultiMethod('find', 4, defaults=(0, maxint))
unicode_index      = MultiMethod('index', 4, defaults=(0, maxint))
unicode_isalnum    = MultiMethod('isalnum', 1)
unicode_isalpha    = MultiMethod('isalpha', 1)
unicode_isdecimal  = MultiMethod('isdecimal', 1)
unicode_isdigit    = MultiMethod('isdigit', 1)
unicode_islower    = MultiMethod('islower', 1)
unicode_isnumeric  = MultiMethod('isnumeric', 1)
unicode_isspace    = MultiMethod('isspace', 1)
unicode_istitle    = MultiMethod('istitle', 1)
unicode_isupper    = MultiMethod('isupper', 1)
unicode_join       = MultiMethod('join', 2)
unicode_ljust      = MultiMethod('ljust', 2)
unicode_lower      = MultiMethod('lower', 1)
unicode_lstrip     = MultiMethod('lstrip', 2, defaults=(None,))
unicode_replace    = MultiMethod('replace', 4, defaults=(-1,))
unicode_rfind      = MultiMethod('rfind', 4, defaults=(0, maxint))
unicode_rindex     = MultiMethod('rindex', 4, defaults=(0, maxint))
unicode_rjust      = MultiMethod('rjust', 2)
unicode_rstrip     = MultiMethod('rstrip', 2, defaults=(None,))
unicode_split      = MultiMethod('split', 3, defaults=(None,-1))
unicode_splitlines = MultiMethod('splitlines', 2, defaults=(0,))
unicode_startswith = MultiMethod('startswith', 3, defaults=(0,))
unicode_strip      = MultiMethod('strip',  2, defaults=(None,))
unicode_swapcase   = MultiMethod('swapcase', 1)
unicode_title      = MultiMethod('title', 1)
unicode_translate  = MultiMethod('translate', 3, defaults=('',))
unicode_upper      = MultiMethod('upper', 1)
unicode_zfill      = MultiMethod('zfill', 2)

# ____________________________________________________________
def descr__new__(space, w_unicodetype, w_obj=None, w_encoding=None, w_errors=None):
    from pypy.objspace.std.unicodeobject import W_UnicodeObject
    w_obj_type = space.type(w_obj)
    
    if space.is_w(w_obj_type, space.w_unicode):
        if space.is_w(w_unicodetype, space.w_unicode):
            return w_obj
        value = space.unwrap(w_obj)
    elif space.is_w(w_obj, space.w_None):
        value = u''
    elif space.is_true(space.isinstance(w_obj, space.w_unicode)):
        value = w_obj._value
    elif space.is_w(w_obj_type, space.w_str):
        try:
            if space.is_w(w_encoding, space.w_None):
                value = unicode(space.str_w(w_obj))
            elif space.is_w(w_errors, space.w_None): 
                value = unicode(space.str_w(w_obj), space.str_w(w_encoding))
            else:
                value = unicode(space.str_w(w_obj), space.str_w(w_encoding),
                                space.str_w(w_errors))
        except UnicodeDecodeError, e:
            raise OperationError(space.w_UnicodeDecodeError, space.wrap(e.reason))
    else:
        raise OperationError(space.w_ValueError, space.wrap('Can not create unicode from other than strings (is %r)'%w_obj_type))
    w_newobj = space.allocate_instance(W_UnicodeObject, w_unicodetype)
    w_newobj.__init__(space, value)
    return w_newobj

# ____________________________________________________________

unicode_typedef = StdTypeDef("unicode", basestring_typedef,
    __new__ = newmethod(descr__new__),
    )
unicode_typedef.registermethods(globals())
