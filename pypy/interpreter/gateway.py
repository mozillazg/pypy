"""

gateway between app-level and interpreter-level 

"""
import inspect
CO_VARARGS, CO_VARKEYWORDS = 0x4, 0x8

class app2interp(object):
    """ this class exposes an app-level defined function at interpreter-level 
        Assumption:  the interp-level function will be called ala

                            a.function(arg1, arg2, argn)

                     with 'a' having an attribute 'space' which the app-level 
                     code should run in. (might change in during the branch)
    """
    def __init__(self, func):
        #print "making app2interp for", func
        self.func = func
        self._codecache = {}

    def __get__(self, instance, cls=None):
        space = instance.space
        try:
            return self._codecache[(space, instance, self)] 
        except KeyError:
            c = InterpretedFunction(space, self.func)
            c.im_self = instance
            assert c.simple, "function should be simple but isn't"
            self._codecache[(space, instance, self)] = c
            return c

class ScopedCode(object):
    """ a code object within a certain global and closure scope.
    (the local scope is given when you call 'eval_frame')
    """
    def __init__(self, space, cpycode, w_globals=None, closure_w=()):
        self.space = space
        self.cpycode = cpycode
        self.w_code = space.wrap(cpycode)
        self.closure_w = closure_w
        if w_globals is None:
            w_globals = space.newdict([])
        self.w_globals = w_globals

    def create_frame(self, w_locals=None):
        """ return result of executing code object within a frame"""
        from pyframe import PyFrame
        frame = PyFrame()
        frame.initialize(self)
        if w_locals is None:
            w_locals = self.w_globals
        frame.setdictscope(w_locals)
        return frame

    def eval_frame(self, *args, **kwargs):
        frame = self.create_frame(*args, **kwargs)
        return self.space.getexecutioncontext().eval_frame(frame)

class InterpretedFunction(ScopedCode):
    """ a function which executes at app-level (by interpreting bytecode
    and dispatching operations on an objectspace). 
    """

    def __init__(self, space, cpyobj, w_globals=None, closure_w=()): 
        """ initialization similar to base class but it also wraps 
        some function-specific stuff (like defaults). 
        """
        if hasattr(cpyobj, 'func_code'):
            self.w_defs = space.wrap(cpyobj.func_defaults or ()) 
            cpycode = cpyobj.func_code
        else:
            self.w_defs = space.newtuple([])
            cpycode = cpyobj
        assert type(self.w_defs) is tuple, "type of desfs is %s" % type(self.w_defs)
        ScopedCode.__init__(self, space, cpycode, w_globals, closure_w)
        self.simple = cpycode.co_flags & (CO_VARARGS|CO_VARKEYWORDS)==0

    def parse_args(self, frame, w_args, w_kwargs):
        """ parse args and kwargs and set fast scope of frame.
        """
        space = self.space
        if hasattr(self, 'im_self'):
            args_w = space.unpacktuple(w_args)
            args_w = [space.wrap(self.im_self)] + args_w
            w_args = space.newtuple(args_w)

        loc_w = None
        if self.simple and (w_kwargs is None or not space.is_true(w_kwargs)):
            try:
                loc_w = space.unpacktuple(w_args, self.cpycode.co_argcount)
            except ValueError:
                pass
        if loc_w is None:
            #print "complicated case of arguments for", self.cpycode.co_name, "simple=", self.simple
            assert type(self.w_defs) is tuple
            w_loc = self.parse_args_complex(self.w_code, w_args, w_kwargs, self.w_defs)
            loc_w = space.unpacktuple(w_loc)
        loc_w.extend([_NULL] * (self.cpycode.co_nlocals - len(loc_w)))

        # make nested cells
        for name in self.cpycode.co_cellvars:
            i = list(self.cpycode.co_varnames).index(name)
            w_value = loc_w[i] 
            loc_w[i] = _NULL
            frame.closure_w += (Cell(w_value),)

        assert len(loc_w) == self.cpycode.co_nlocals, "local arguments not prepared correctly"
        frame.setfastscope(loc_w)

    def __get__(self, instance, cls=None):
        func = object.__new__(self.__class__)
        func.__dict__.update(self.__dict__)
        func.im_self = instance
        return func

    def create_frame(self, w_args, w_kwargs):
        """ parse arguments and execute frame """
        from pyframe import PyFrame
        frame = PyFrame()
        frame.initialize(self)
        self.parse_args(frame, w_args, w_kwargs)
        return frame

    def parse_args_complex_w(self, cpycode, args, kwargs, defs):
        """ return list of initial local values parsed from 
        'args', 'kwargs' and defaults.
        """
        #if cpycode.co_name == 'failUnlessRaises':
        #    print "co_name", cpycode.co_name
        #    print "co_argcount", cpycode.co_argcount
        #    print "co_nlocals", cpycode.co_nlocals
        #    print "co_varnames", cpycode.co_varnames
        #    print "args", args
        #    print "kwargs", kwargs
        #    print "defs", defs

        CO_VARARGS, CO_VARKEYWORDS = 0x4, 0x8

        #   co_argcount number of expected positional arguments 
        #   (elipsis args like *args and **kwargs do not count) 
        co_argcount = cpycode.co_argcount

        # construct list of positional args 
        positional_args = list(args[:co_argcount])

        len_args = len(args)
        len_defs = len(defs)

        if len_args < co_argcount:
            # not enough args, fill in kwargs or defaults if exists
            i = len_args
            while i < co_argcount:
                name = cpycode.co_varnames[i]
                if name in kwargs:
                    positional_args.append(kwargs[name])
                    del kwargs[name]
                else:
                    if i + len_defs < co_argcount:
                        raise TypeError, "Not enough arguments"
                    positional_args.append(defs[i-co_argcount])
                i+=1
        if cpycode.co_flags & CO_VARARGS:
            positional_args.append(tuple(args[co_argcount:]))
        elif len_args > co_argcount:
            raise TypeError, "Too many arguments"

        i = 0
        while i < len_args and i < co_argcount:
            name = cpycode.co_varnames[i]
            if name in kwargs:
                raise TypeError, "got multiple values for argument %r" % name
            i+=1


        # XXX probably need an extra pass over kwargs to determine if a 
        #     keyword-arg sets a second time 
        if cpycode.co_flags & CO_VARKEYWORDS:
            positional_args.append(kwargs)
        elif kwargs:
            raise TypeError, "got unexpected keyword argument(s) %s" % repr(kwargs.keys()[0])

        return positional_args
    parse_args_complex = app2interp(parse_args_complex_w)

    def __call__(self, *args_w, **kwargs_w):
        """ call with native parameter passing convention """
        #print "native call on", self.cpycode.co_name
        #print "len args_w", len(args_w)
        #print "kwargs_w", kwargs_w
        w_args = self.space.newtuple(args_w)
        w = self.space.wrap
        w_kwargs = self.space.newdict([])
        for name, w_value in kwargs_w.items():
            self.space.setitem(w_kwargs, w(name), w_value)
        return self.eval_frame(w_args, w_kwargs)

class AppVisibleModule:
    """ app-level visible Module defined at interpreter-level.

    Inherit from this class if you want to have a module that accesses
    the PyPy interpreter (e.g. builtins like 'locals()' require accessing the
    frame). You can mix in application-level code by prefixing your method
    with 'app_'. Both non-underscore methods and app-level methods will
    be available on app-level with their respective name. 

    On __wrap__(space) it returns an app-level (read: wrapped) module object. 

    functions prefixed with 'app_' indicate app-level running functions.
    Note that these functions don't get a 'self' argument because we really
    need only the function (there is no notion of beeing 'bound' or 'unbound' 
    for them).
    
    """
    def __init__(self, space):
        self.space = space

        if hasattr(self, '_wrap_postponed'):
            self._postponed = []

        space = self.space
        modname = self.__class__.__name__
        self.w___name__ = space.wrap(modname)
        self._wrapped = _wrapped = space.newmodule(self.w___name__)

        # go through all items in the module class instance
        for name in dir(self):
            # skip spurious info and internal methods
            if name == '__module__' or name.startswith('_') and not name.endswith('_'):
                #print modname, "skipping", name
                continue
            obj = getattr(self, name)
            # see if we just need to expose an already wrapped value
            if name.startswith('w_'):
                space.setattr(_wrapped, space.wrap(name[2:]), obj)

            # see if have something defined at app-level
            elif name.startswith('app_'):
                obj = self.__class__.__dict__.get(name)
                name = name[4:]

                # just a simple function? 
                if hasattr(obj, 'func_code'):
                    w_res = space.wrap(InterpretedFunction(space, obj))

                # or a class? (which eventually needs to be recompiled)
                elif inspect.isclass(obj):
                    # this module chooses to do this later (usually
                    # for bootstrapping reasons)
                    if hasattr(self, '_postponed'):
                        self._postponed.append((name, obj))
                    else:
                        w_res = wrap_applevel_class(space, name, obj)
                else:
                    raise ValueError, "cannot wrap %s, %s" %(name, obj)

            else:
                w_res = wrap_interplevel(space, name, obj)
                setattr(self, 'w_'+name, w_res)
            w_name = space.wrap(name)
            space.setattr(_wrapped, w_name, w_res)

def wrap_applevel(space, name, obj):
    """ wrap an app-level object which was compiled/lives 
    at interpreter-level.
    """
    #print "app registering ", name #, obj
    if hasattr(obj, 'func_code'):
        return space.wrap(InterpretedFunction(space, obj))
    elif inspect.isclass(obj):
        return wrap_applevel_class(space, name, obj)
    else:
        raise ValueError, "cannot wrap %s, %s" % (name, obj)

def wrap_applevel_class(space, name, obj):
    """ construct an app-level class by reproducing the
    source definition and running it through the interpreter.
    It's a bit ugly but i don't know a better way (holger). 
    """
    l = ['class %s:' % name]
    indent = '    '
    for key, value in vars(obj).items():
        if hasattr(value, 'func_code'):
            s = inspect.getsource(value)
            l.append(s)
            indent = " " * (len(s) - len(s.lstrip()))

    if getattr(obj, '__doc__', None):
        l.insert(1, indent + obj.__doc__)

    for key, value in vars(obj).items():
        if not key in ('__module__', '__doc__'):
            if isinstance(value, (str, int, float, tuple, list)):
                l.append('%s%s = %r' % (indent, key, value))

    s = "\n".join(l)
    code = compile(s, s, 'exec')
    scopedcode = ScopedCode(space, code, None)
    scopedcode.eval_frame()
    w_name = space.wrap(name)
    w_res = space.getitem(scopedcode.w_globals, w_name)
    return w_res

def wrap_interplevel(space, name, obj):
    """ wrap an app-level object which was compiled/lives 
    at interpreter-level.
    """
    return space.wrap(obj)


## Cells (used for nested scopes only) ##

_NULL = object() # Marker object

class Cell:
    def __init__(self, w_value=_NULL):
        self.w_value = w_value

    def clone(self):
        return self.__class__(self.w_value)

    def get(self):
        if self.w_value is _NULL:
            raise ValueError, "get() from an empty cell"
        return self.w_value

    def set(self, w_value):
        self.w_value = w_value

    def delete(self):
        if self.w_value is _NULL:
            raise ValueError, "make_empty() on an empty cell"
        self.w_value = _NULL

    def __repr__(self):
        """ representation for debugging purposes """
        if self.w_value is _NULL:
            return "%s()" % self.__class__.__name__
        else:
            return "%s(%s)" % (self.__class__.__name__, self.w_value)


