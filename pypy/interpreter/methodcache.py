"""
"""

from pypy.interpreter import baseobjspace, typedef
from pypy.interpreter.function import Function


class MethodCache(baseobjspace.Wrappable):

    cached_tag        = None
    w_cached_function = None

    def __init__(self, attrname, argkwcount):
        self.attrname = attrname
        self.argkwcount = argkwcount

    def load_cache(self, space, w_type, version_tag):
        w_class, w_value = space.lookup_in_type_where(w_type,
                                                      '__getattribute__')
        if w_class is not None and space.is_w(w_class, space.w_object):
            # no special __getattribute__, so we can perform the
            # lookup of the attrname in the usual way
            w_class, w_value = space.lookup_in_type_where(w_type,
                                                          self.attrname)
            if type(w_value) is Function:
                # cache the Function object
                self.cached_tag        = version_tag
                self.w_cached_function = w_value
                return True
        # not the common case - no caching
        self.cached_tag        = None
        self.w_cached_function = None
        return False

    def call_args(self, space, w_obj, args):
        w_type = space.type(w_obj)
        version_tag = space.gettypeversion(w_type)
        if version_tag is self.cached_tag or self.load_cache(space, w_type,
                                                             version_tag):
            w_value = w_obj.getdictvalue_w(space, self.attrname)
            if w_value is None:
                # no method shadowing (this is the common situation that we
                # are trying to make as fast as possible)
                args = args.prepend(w_obj)
                return space.call_args(self.w_cached_function, args)
        else:
            # fallback
            w_value = space.getattr(w_obj, space.wrap(self.attrname))
        return space.call_args(w_value, args)

    def call_valuestack(self, space, valuestack):
        nargs = self.argkwcount
        w_obj = valuestack.top(nargs)
        w_type = space.type(w_obj)
        version_tag = space.gettypeversion(w_type)
        if version_tag is self.cached_tag or self.load_cache(space, w_type,
                                                             version_tag):
            w_value = w_obj.getdictvalue_w(space, self.attrname)
            if w_value is None:
                # no method shadowing (this is the common situation that we
                # are trying to make as fast as possible)
                return self.w_cached_function.funccall_valuestack(nargs + 1,
                                                                  valuestack)
        else:
            # fallback
            w_value = space.getattr(w_obj, space.wrap(self.attrname))
        return space.call_valuestack(w_value, nargs, valuestack)


MethodCache.typedef = typedef.TypeDef("method_cache")
