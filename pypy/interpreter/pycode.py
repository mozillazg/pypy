"""
PyCode class implementation.

This class is similar to the built-in code objects.
It avoids wrapping existing code object, instead,
it plays its role without exposing real code objects.
SInce in C Python the only way to crate a code object
by somehow call into the builtin compile, we implement
the creation of our code object by defining out own compile,
wich ()at the moment) calls back into the real compile,
hijacks the code object and creates our code object from that.
compile is found in the builtin.py file.
"""

# XXX todo:
# look at this if it makes sense
# think of a proper base class???

import baseobjspace, executioncontext

CO_VARARGS     = 0x0004
CO_VARKEYWORDS = 0x0008

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
            c = AppBuiltinCode(space, self.func, instance)
            self._codecache[(space, instance, self)] = c
            return c
        
class PyBaseCode(object):
    def __init__(self):
        self.co_name = ""
        self.co_flags = 0
        self.co_varnames = ()
        self.co_argcount = 0
        self.co_freevars = ()
        self.co_cellvars = ()
        
    def build_arguments(self, space, w_arguments, w_kwargs, w_defaults, w_closure):
        # We cannot systematically go to the application-level (_app.py)
        # to do this dirty work, for bootstrapping reasons.  So we check
        # if we are in the most simple case and if so do not go to the
        # application-level at all.
        co = self
        if (co.co_flags & (CO_VARARGS|CO_VARKEYWORDS) == 0 and
            (w_kwargs   is None or not space.is_true(w_kwargs))   and
            (w_closure  is None or not space.is_true(w_closure))):
            # looks like a simple case, see if we got exactly the correct
            # number of arguments
            try:
                args = space.unpacktuple(w_arguments, self.co_argcount)
            except ValueError:
                pass  # no
            else:
                # yes! fine!
                argnames = [space.wrap(name) for name in co.co_varnames]
                w_arguments = space.newdict(zip(argnames, args))
                return w_arguments
        # non-trivial case.  I won't do it myself.
        if w_kwargs   is None: w_kwargs   = space.newdict([])
        if w_defaults is None: w_defaults = space.newtuple([])
        if w_closure  is None: w_closure  = space.newtuple([])
        w_bytecode = space.wrap(co)

        self.space = space
        w_locals = self.decode_code_arguments(w_arguments, w_kwargs, 
                                         w_defaults, w_bytecode)
        if space.is_true(w_closure):
            l = zip(co.co_freevars, space.unpackiterable(w_closure))
            for key, w_cell in l:
                space.setitem(w_locals, space.wrap(key), w_cell)
        return w_locals

    def app_decode_code_arguments(self, args, kws, defs, codeobject):
        """
        Assumptions:
        args       sequence of the normal actual parameters
        kws        dictionary of keyword actual parameters
        defs       sequence of defaults
        codeobject our code object carrying argument info
        """
        CO_VARARGS = 0x4
        CO_VARKEYWORDS = 0x8
        varargs = (codeobject.co_flags & CO_VARARGS) and 1
        varkeywords = (codeobject.co_flags & CO_VARKEYWORDS) and 1
        varargs_tuple = ()

        argdict = {}
        parameter_names = codeobject.co_varnames[:codeobject.co_argcount]

        # Normal arguments
        for i in range(0, len(args), 1):    # see comment above for ", 1"
            if 0 <= i < len(parameter_names): # try
                argdict[parameter_names[i]] = args[i]
            else: # except IndexError:
                # If varargs, put in tuple, else throw error
                if varargs:
                    varargs_tuple = args[i:]
                else:
                    raise TypeError, 'Too many parameters to callable object'
                break

        # Put all suitable keywords into arglist
        if kws:
            if varkeywords:
                # Allow all keywords
                newkw = {}
                for key in kws.keys():
                    for name in parameter_names:
                        if name == key:
                            if key in argdict:
                                raise TypeError, 'Setting parameter %s twice.' % name
                            else:
                                argdict[key] = kws[key]
                            break # name found in parameter names
                    else:
                        newkw[key] = kws[key]

            else:
                # Only allow formal parameter keywords
                count = len(kws)
                for name in parameter_names:
                    if name in kws:
                        count -= 1
                        if name in argdict:
                            raise TypeError, 'Setting parameter %s twice.' % name
                        else:
                            argdict[name] = kws[name]
                if count:
                    # XXX This should be improved to show the parameters that
                    #     shouldn't be here.
                    raise TypeError('Setting keyword parameter that does '
                                    'not exist in formal parameter list.')
        else:
            newkw = {}

        # Fill in with defaults, starting at argcount - defcount
        if defs:
            argcount = codeobject.co_argcount
            defcount = len(defs)
            for i in range(argcount - defcount, argcount, 1): # ", 1" comment above
                if parameter_names[i] in argdict:
                    continue
                argdict[parameter_names[i]] = defs[i - (argcount - defcount)]

        if len(argdict) < codeobject.co_argcount:
            raise TypeError, 'Too few parameters to callable object'

        namepos = codeobject.co_argcount
        if varargs:
            name = codeobject.co_varnames[namepos]
            argdict[name] = varargs_tuple
            namepos += 1
        if varkeywords:
            name = codeobject.co_varnames[namepos]
            argdict[name] = newkw

        return argdict

    decode_code_arguments = app2interp(app_decode_code_arguments)

        
class PyByteCode(PyBaseCode):
    """Represents a code object for Python functions.

    Public fields:
    to be done
    """

    def __init__(self):
        """ initialize all attributes to just something. """
        PyBaseCode.__init__(self)
        self.co_filename = ""
        self.co_code = None
        self.co_consts = ()
        self.co_names = ()
        self.co_nlocals = 0
        self.co_stacksize = 0
        # The rest doesn't count for hash/cmp
        self.co_firstlineno = 0 #first source line number
        self.co_lnotab = "" # string (encoding addr<->lineno mapping)
        
    ### codeobject initialization ###

    def _from_code(self, code):
        """ Initialize the code object from a real one.
            This is just a hack, until we have our own compile.
            At the moment, we just fake this.
            This method is called by our compile builtin function.
        """
        import types
        assert type(code) is types.CodeType
        # simply try to suck in all attributes we know of
        for name in self.__dict__.keys():
            value = getattr(code, name)
            setattr(self, name, value)
        newconsts = ()
        for const in code.co_consts:
            if isinstance(const, types.CodeType):
                newc = PyByteCode()
                newc._from_code(const)
                newconsts = newconsts + (newc,)
            else:
                newconsts = newconsts + (const,)
        self.co_consts = newconsts

    def eval_code(self, space, w_globals, w_locals):
        from pypy.interpreter import pyframe
        frame = pyframe.PyFrame(space, self, w_globals, w_locals)
        ec = space.getexecutioncontext()
        w_ret = ec.eval_frame(frame)
        return w_ret

    def locals2cells(self, space, w_locals):
        from pypy.interpreter import pyframe
        localcells = []
        Cell = pyframe.Cell
        for name in self.co_varnames:
            w_name = space.wrap(name)
            try:
                w_value = space.getitem(w_locals, w_name)
            except executioncontext.OperationError, e:
                if not e.match(space, space.w_KeyError):
                    raise
                else:
                    cell = Cell()
            else:
                cell = Cell(w_value)
            localcells.append(cell)
        nestedcells = []
        for name in self.co_cellvars:
            cell = Cell()
            nestedcells.append(cell)
        for name in self.co_freevars:
            w_name = space.wrap(name)
            w_cell = space.getitem(w_locals, w_name)
            cell = space.unwrap(w_cell)
            nestedcells.append(cell)
        return localcells, nestedcells

class AppBuiltinCode:
    """The code object implementing a app-level hook """

    def __init__(self, space, func, instance=None):
        assert func.func_code.co_flags & (CO_VARARGS|CO_VARKEYWORDS) == 0
        self.space = space

        #PyBaseCode.__init__(self)
        co = func.func_code

        self.instance = instance
        self.func = func
        self.co_code = co.co_code
        self.co_name = func.__name__
        self.co_consts = co.co_consts
        self.co_flags = co.co_flags
        self.co_varnames = tuple(co.co_varnames)
        self.co_nlocals = co.co_nlocals
        self.co_argcount = co.co_argcount 
        self.co_names = co.co_names
        self.next_arg = self.co_argcount 

    def __call__(self, *args_w):
        from pypy.interpreter import pyframe
        w_globals = self.space.newdict([])
        if self.instance:
            args_w = (self.space.wrap(self.instance),) + args_w  # effects untested
        frame = pyframe.AppFrame(self.space, self, w_globals, args_w)
        ec = self.space.getexecutioncontext()
        w_ret = ec.eval_frame(frame)
        return w_ret
