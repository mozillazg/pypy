"""
Function objects.

In PyPy there is no difference between built-in and user-defined function
objects; the difference lies in the code object found in their func_code
attribute.
"""

class Function:
    """A function is a code object captured with some environment:
    an object space, a dictionary of globals, default arguments,
    and an arbitrary 'closure' passed to the code object."""
    
    def __init__(self, space, code, w_globals, w_defs=None, closure=None):
        self.space     = space
        self.func_code = code       # Code instance
        self.w_globals = w_globals  # the globals dictionary
        self.w_defs    = w_defs     # wrapped sequence of default args or None
        self.closure   = closure    # normally, list of Cell instances or None

    def parse_args(self, frame, w_args, w_kwargs=None):
        """ parse args and kwargs to initialize the frame.
        """
        space = self.space
        signature = self.func_code.signature()
        argnames, varargname, kwargname = signature
        # test for 'simple case':
        if (varargname is None and kwargname is None and          # no */**
            (w_kwargs is None or not space.is_true(w_kwargs)) and # no kwargs
            self.unwrap(self.len(w_args)) == len(argnames)):  # correct #args
            for index in range(len(argnames)):
                w_index = self.wrap(index)
                w_argument = self.getitem(w_args, w_index)
                frame.setlocalvar(index, w_argument)
        else:
            #print "complicated case of arguments for", self.func_code.co_name
            if w_kwargs is None:
                w_kwargs = space.w_None
            self.parse_args_complex(frame, w_args, w_kwargs,
                                    space.wrap(signature))
        frame.setclosure(self.closure)

    def app_parse_args_complex(self, frame, args, kws, signature):
        """ app-level helper for the complex case of parse_args().
        """
        # ===== ATTENTION =====
        #
        # This code is pretty fundamental to pypy and great care must be taken
        # to avoid infinite recursion.  In particular:
        #
        # - All calls here must be "easy", i.e. not involve default or keyword
        #   arguments.  For example, all range() calls need three arguments.
        #
        # - You cannot *catch* any exceptions (raising is fine).
        #
        # Assumptions:
        #   frame = empty frame to be initialized
        #   args = sequence of the normal actual parameters
        #   kws = dictionary of keyword parameters or None
        #   self.defs = sequence of defaults
        #
        # We try to give error messages following CPython's, which are
        # very informative.

        argnames, varargname, kwargname = signature
        input_argcount = len(args)
        co_argcount = len(argnames)
        deffirst = co_argcount - len(self.defs)
        if kws:
            kwargs = kws.copy()
        else:
            kwargs = {}

        # fetch all arguments left-to-right
        for i in range(0, co_argcount, 1):
            argname = argnames[i]
            if i < input_argcount:
                value = args[i]
                # check that no keyword argument also gives a value here
                if argname in kwargs:
                    raise TypeError, self.argerr_multiple_values(argname)
            elif argname in kwargs:
                # positional arguments exhausted,
                # complete with keyword arguments
                value = kwargs[argname]
                del kwargs[argname]
            elif i >= deffirst:
                # no matching keyword argument, but there is a default value
                value = self.defs[i - deffirst]
            else:
                raise TypeError, self.argerr(signature, args, kws, False)
            frame.setlocalvar(i, value)

        # collect extra positional arguments into the *vararg
        specialarg = co_argcount
        if varargname is not None:
            var_tuple = args[co_argcount:]
            frame.setlocalvar(specialarg, var_tuple)
            specialarg += 1
        elif input_argcount > co_argcount:
            # cannot do anything with these extra positional arguments
            raise TypeError, self.argerr(signature, args, kws, True)

        # collect extra keyword arguments into the **kwarg
        if kwargname is not None:
            # XXX this doesn't check that the keys of kwargs are strings
            frame.setlocalvar(specialarg, kwargs)
            specialarg += 1
        elif kwargs:
            # cannot do anything with these extra keyword arguments
            raise TypeError, self.argerr_unknown_kwds(kwargs)
    parse_args_complex = app2interp(app_parse_args_complex)

    # helper functions to build error message for the above

    def app_argerr(self, signature, args, kws, too_many):
        argnames, varargname, kwargname = signature
        n = len(argnames)
        if n == 0:
            n = len(args)
            if kwargname is not None:
                msg2 = "non-keyword "
            else:
                msg2 = ""
                n += len(kws)
            return "%s() takes no %sargument (%d given)" % (
                self.func_code.co_name,
                msg2,
                n)
        else:
            defcount = len(self.defs)
            if defcount == 0:
                msg1 = "exactly"
            elif too_many:
                msg1 = "at most"
            else:
                msg1 = "at least"
                n -= defcount
            if kws:
                msg2 = "non-keyword "
            else:
                msg2 = ""
            if n == 1:
                plural = ""
            else:
                plural = "s"
            return "%s() takes %s %d %sargument%s (%d given)" % (
                self.func_code.co_name,
                msg1,
                n,
                msg2,
                plural,
                len(args))

    def app_argerr_multiple_values(self, argname):
        return "%s() got multiple values for keyword argument %s" % (
            self.func_code.co_name,
            argname)

    def app_argerr_unknown_kwds(self, kws):
        if len(kws) == 1:
            return "%s() got an unexpected keyword argument '%s'" % (
                self.func_code.co_name,
                kws.keys()[0])
        else:
            return "%s() got %d unexpected keyword arguments" % (
                self.func_code.co_name,
                len(kws))
