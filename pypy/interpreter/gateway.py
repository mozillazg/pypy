"""

Gateway between app-level and interpreter-level:
* BuiltinCode (call interp-level code from app-level)
* app2interp  (embed an app-level function into an interp-level callable)
* interp2app  (publish an interp-level object to be visible from app-level)
* publishall  (mass-call interp2app on a whole list of objects)

"""

#
# XXX warning, this module is a bit scary in the number of classes that
#     all play a similar role but in slightly different contexts
#

import types
from pypy.interpreter import eval, pycode
from pypy.interpreter.baseobjspace import Wrappable, ObjSpace
from pypy.interpreter.function import Function


class BuiltinCode(eval.Code):
    "The code object implementing a built-in (interpreter-level) hook."

    # When a BuiltinCode is stored in a Function object,
    # you get the functionality of CPython's built-in function type.

    def __init__(self, func, **argflags):
        # 'implfunc' is the interpreter-level function.
        # See below for 'argflags'.
        # Note that this uses a lot of (construction-time) introspection.
        eval.Code.__init__(self, func.__name__)
        self.func = func
        self.argflags = argflags
        # extract the signature from the (CPython-level) code object
        tmp = pycode.PyCode(None)
        tmp._from_code(func.func_code)
        self.sig = tmp.signature()
        if isinstance(func, types.MethodType) and func.im_self is not None:
            argnames, varargname, kwargname = self.sig
            argnames = argnames[1:]  # implicit hidden self argument
            self.sig = argnames, varargname, kwargname
        self.nargs = len(self.getvarnames())

    def bind_code(self, instance):
        """Create another version of this code object that calls 'func'
        as a method, with implicit first argument 'instance'."""
        return BuiltinCode(self.func.__get__(instance, instance.__class__),
                           **self.argflags)

    def create_frame(self, space, w_globals, closure=None):
        return BuiltinFrame(space, self, w_globals, numlocals=self.nargs)

    def signature(self):
        return self.sig

# An application-level function always implicitely expects wrapped arguments,
# but not an interpreter-level function not. The extra keywords given to the
# constructor of BuiltinCode describes what kind of arguments 'func' expects.
#
# Default signature:
#   def func(space, w_arg1, w_arg2...)            <- plain functions
#   def func(self, space, w_arg1, w_arg2...)      <- methods
#
# Flags:  (XXX need more)
#   implicitspace=True    method with no 'space' arg. We use 'self.space'
#   implicitself=True     the app-level doesn't see any 'self' argument


class BuiltinFrame(eval.Frame):
    "Frame emulation for BuiltinCode."
    # This is essentially just a delegation to the 'func' of the BuiltinCode.
    # Initialization of locals is already done by the time run() is called,
    # via the interface defined in eval.Frame.

    def run(self):
        argarray = self.fastlocals_w
        if not self.code.argflags.get('implicitspace'):
            argarray = [space] + argarray
        return call_with_prepared_arguments(self.space, self.code.func,
                                            argarray)


def call_with_prepared_arguments(space, function, argarray):
    """Call the given function. 'argarray' is a correctly pre-formatted
    list of values for the formal parameters, including one for * and one
    for **."""
    # XXX there is no clean way to do this in Python,
    # we have to hack back an arguments tuple and keywords dict.
    # This algorithm is put in its own well-isolated function so that
    # you don't need to look at it :-)
    keywords = {}
    co = function.func_code
    if co.co_flags & 8:  # CO_VARKEYWORDS
        w_kwds = argarray[-1]
        for w_key in space.unpackiterable(w_kwds):
            keywords[space.unwrap(w_key)] = space.getitem(w_kwds, w_key)
        argarray = argarray[:-1]
    if co.co_flags & 4:  # CO_VARARGS
        w_varargs = argarray[-1]
        argarray = argarray[:-1] + space.unpacktuple(w_varargs)
    return function(*argarray, **keywords)


class Gateway(object):
    # General-purpose utility for the interpreter-level to create callables
    # that transparently invoke code objects (and thus possibly interpreted
    # app-level code).

    # 'argflags' controls how the Gateway instance should decode its
    # arguments. It only influences calls made from interpreter-level.
    # It has the same format as BuiltinCode.argflags.

    def __init__(self, code, staticglobals, staticdefs=[], **argflags):
        self.code = code
        self.staticglobals = staticglobals  # a DictProxy instance
        self.staticdefs = staticdefs
        self.argflags = argflags

    def make_function(self, space, bind_instance=None, w_globals=None):
        if w_globals is None:
            #w_globals = space.wrap(self.staticglobals)
            w_globals = self.staticglobals.makedict(space, bind_instance)
        defs_w = [space.wrap(def_value) for def_value in self.staticdefs]
        code = self.code
        if self.argflags.get('implicitself') and isinstance(code, BuiltinCode):
            assert bind_instance is not None, ("built-in function can only "
                                               "be used as a method")
            code = code.bind_code(bind_instance)
        return Function(space, code, w_globals, defs_w)

    def __wrap__(self, space):
        # to wrap a Gateway, we first make a real Function object out of it
        # and the result is a wrapped version of this Function.
        return space.wrap(self.make_function(space))

    def __call__(self, space, *args, **kwds):
        wrap = space.wrap
        w_args = [wrap(arg) for arg in args]
        w_kwds = space.newdict([(wrap(key), wrap(value))
                                for key, value in kwds.items()])
        fn = self.make_function(space)
        return fn.call(w_args, w_kwds)

    def __get__(self, obj, cls=None):
        if obj is None:
            return self
        else:
            return BoundGateway(self, obj)


class BoundGateway(object):

    def __init__(self, gateway, obj):
        self.gateway = gateway
        self.obj = obj

    def __call__(self, *args, **kwds):
        if self.gateway.argflags.get('implicitspace'):
            # we read 'self.space' from the object we are bound to
            space = self.obj.space
        else:
            space = args[0]  # explicit 'space' as a first argument
            args = args[1:]
            if not isinstance(space, ObjSpace):
                raise TypeError, "'space' expected as first argument"
        wrap = space.wrap
        if self.gateway.argflags.get('implicitself'):
            pass  # app-space gets no 'self' argument
        else:
            args = (wrap(self.obj),) + args  # insert 'w_self'
        w_args = [wrap(arg) for arg in args]
        w_kwds = space.newdict([(wrap(key), wrap(value))
                                for key, value in kwds.items()])
        fn = self.gateway.make_function(space, self.obj)
        return fn.call(w_args, w_kwds)


class DictProxy(Wrappable):
    # This class exposes at app-level a read-only dict-like interface.
    # The items in the DictProxy are not wrapped (they are independent
    # of any object space, and are just interpreter-level objects) until
    # app-level code reads them.

    # Instances of DictProxy play the role of the 'globals' for app-level
    # helpers. This is why app2interp and interp2app are methods of
    # DictProxy. Calling them on the same DictProxy for several functions
    # gives all these functions the same 'globals', allowing them to see
    # and call each others.

    # XXX a detail has been (temporarily?) changed because too many
    # places (notably in pyopcode.py) assume that the globals should
    # satisfy 'instance(globals, dict)'. Now wrapping a DictProxy
    # gives you a real dict.

    def __init__(self, basedict=None, **defaultargflags):
        if basedict is None:
            self.content = {}
        else:
            self.content = basedict.content.copy()
        self.defaultargflags = defaultargflags

    #def __getitem__(self, key):
    #    return self.content[key]
    #
    #def __iter__(self):
    #    return iter(self.content)
    def __wrap__(self, space):
        return self.makedict(space)

    def app2interp(self, app, app_name=None, **argflags):
        """Build a Gateway that calls 'app' at app-level and insert it
        into the DictProxy."""
        # app must be a function whose name starts with 'app_'
        if not isinstance(app, types.FunctionType):
            raise TypeError, "function expected, got %r instead" % app
        if app_name is None:
            if not app.func_name.startswith('app_'):
                raise ValueError, ("function name must start with 'app_'; "
                                   "%r does not" % app.func_name)
            app_name = app.func_name[4:]
        argflags1 = self.defaultargflags.copy()
        argflags1.update(argflags)
        code = pycode.PyCode(None)
        code._from_code(app.func_code)
        staticdefs = list(app.func_defaults or ())
        gateway = Gateway(code, self, staticdefs, **argflags1)
        self.content[app_name] = gateway
        return gateway

    def interp2app(self, f, **argflags):
        """Insert an interp-level function into the DictProxy to make
        it callable from app-level."""
        # f must be a function whose name does NOT starts with 'app_'
        if not isinstance(f, types.FunctionType):
            raise TypeError, "function expected, got %r instead" % f
        assert not f.func_name.startswith('app_'), (
            "function name %r suspiciously starts with 'app_'" % f.func_name)
        argflags1 = self.defaultargflags.copy()
        argflags1.update(argflags)
        builtincode = BuiltinCode(f, **argflags1)
        staticdefs = list(f.func_defaults or ())
        gateway = Gateway(builtincode, self, staticdefs, **argflags1)
        self.content[f.func_name] = gateway

    def exportname(self, name, obj, optional=0):
        """Publish an object of the given name by inserting it into the
        DictProxy. See implementation for the known types of 'obj'."""
        if name.startswith('app_'):
            publicname = name[4:]
            optional = 0
        else:
            publicname = name
        if isinstance(obj, types.FunctionType):
            assert name == obj.func_name
            if name == publicname:
                # an interpreter-level function
                self.interp2app(obj)
            else:
                # an app-level function
                self.app2interp(obj)
        elif not optional:
            # assume a simple, easily wrappable object
            self.content[publicname] = obj
        # else skip the object if we cannot recognize it

    def exportall(self, d):
        """Publish every object from a dict."""
        for name, obj in d.items():
            # ignore names in '_xyz'
            if not name.startswith('_') or name.endswith('_'):
                self.exportname(name, obj, optional=1)

    def importall(self, d, cls=None):
        """Import all app_-level functions as Gateways into a dict.
        Also import literals whose name starts with 'app_'."""
        for name, obj in d.items():
            if name.startswith('app_') and name[4:] not in d:
                if isinstance(obj, types.FunctionType):
                    # an app-level function
                    assert name == obj.func_name
                    obj = self.app2interp(obj)
                else:
                    pass  # assume a simple, easily wrappable object
                if cls is None:
                    d[name[4:]] = obj
                else:
                    setattr(cls, name[4:], obj)

    def makedict(self, space, bind_instance=None):
        """Turn the proxy into a normal dict.
        Gateways to interpreter-level functions that were defined
        with 'implicitself' are bound to 'bind_instance', so that
        calling them from app-space will add this extra hidden argument."""
        w_dict = space.newdict([])
        for key, value in self.content.items():
            if isinstance(value, Gateway):
                value = value.make_function(space, bind_instance, w_dict)
            space.setitem(w_dict, space.wrap(key), space.wrap(value))
        return w_dict
