"""
Arguments objects.
"""

from pypy.interpreter.error import OperationError

class AbstractArguments:
    def frompacked(space, w_args=None, w_kwds=None):
        """Convenience static method to build an Arguments
           from a wrapped sequence and a wrapped dictionary."""
        return Arguments(space, [], w_stararg=w_args, w_starstararg=w_kwds)
    frompacked = staticmethod(frompacked)

    def fromshape(space, (shape_cnt,shape_keys,shape_star,shape_stst), data_w):
        args_w = data_w[:shape_cnt]
        p = shape_cnt
        kwds_w = {}
        for i in range(len(shape_keys)):
            kwds_w[shape_keys[i]] = data_w[p]
            p += 1
        if shape_star:
            w_star = data_w[p]
            p += 1
        else:
            w_star = None
        if shape_stst:
            w_starstar = data_w[p]
            p += 1
        else:
            w_starstar = None
        return Arguments(space, args_w, kwds_w, w_star, w_starstar)
    fromshape = staticmethod(fromshape)

    def prepend(self, w_firstarg):
        "Return a new Arguments with a new argument inserted first."
        return ArgumentsPrepended(self, w_firstarg)
    

class ArgumentsPrepended(AbstractArguments):
    def __init__(self, args, w_firstarg):
        self.args = args
        self.w_firstarg = w_firstarg
        
    def firstarg(self):
        "Return the first argument for inspection."
        return self.w_firstarg

    def __repr__(self):
        return 'ArgumentsPrepended(%r, %r)' % (self.args, self.w_firstarg)

    def has_keywords(self):
        return self.args.has_keywords()

    def unpack(self):
        arguments_w, kwds_w = self.args.unpack()
        return ([self.w_firstarg] + arguments_w), kwds_w

    def fixedunpack(self, argcount):
        if argcount <= 0:
            raise ValueError, "too many arguments (%d expected)" % argcount # XXX: Incorrect
        return [self.w_firstarg] + self.args.fixedunpack(argcount - 1)
        
    def _rawshape(self, nextra=0):
        return self.args._rawshape(nextra + 1)

    def _unpack_stararg(self):
        self.args._unpack_stararg()
        
    def parse(self, fnname, signature, defaults_w=[]):
        """Parse args and kwargs to initialize a frame
        according to the signature of code object.
        """
        self._unpack_stararg()
        try:
            return self.match_signature(signature, defaults_w)
        except ArgErr, e:
            raise OperationError(self.args.space.w_TypeError,
                                 self.args.space.wrap(e.getmsg(self, fnname)))

    def match_signature(self, signature, defaults_w=[]):
        """Parse args and kwargs according to the signature of a code object,
        or raise an ArgErr in case of failure.
        """
        argnames, varargname, kwargname = signature
        scope_w = self.args.match_signature((argnames[1:], varargname, kwargname), defaults_w)
        if len(argnames) == 0:
            if varargname is None:
                raise ArgErrCount(signature, defaults_w, 0)
            space = self.args.space
            if kwargname is not None:
                scope_w[-2] = space.newtuple([self.w_firstarg] + space.unpackiterable(scope_w[-2]))
            else:
                scope_w[-1] = space.newtuple([self.w_firstarg] + space.unpackiterable(scope_w[-1]))
        else:
            scope_w.insert(0, self.w_firstarg)
        return scope_w
    
    def flatten(self):
        (shape_cnt, shape_keys, shape_star, shape_stst), data_w = self.args.flatten()
        data_w.insert(0, self.w_firstarg)
        return (shape_cnt + 1, shape_keys, shape_star, shape_stst), data_w

        
class Arguments(AbstractArguments):
    """
    Collects the arguments of a function call.
    
    Instances should be considered immutable.
    """

    ###  Construction  ###

    blind_arguments = 0

    def __init__(self, space, args_w=None, kwds_w=None,
                 w_stararg=None, w_starstararg=None):
        self.space = space
        self.arguments_w = args_w
        self.kwds_w = kwds_w
        self.w_stararg = w_stararg
        self.w_starstararg = w_starstararg

    def __repr__(self):
        if self.w_starstararg is not None:
            return 'Arguments(%s, %s, %s, %s)' % (self.arguments_w,
                                                  self.kwds_w,
                                                  self.w_stararg,
                                                  self.w_starstararg)
        if self.w_stararg is None:
            if not self.kwds_w:
                return 'Arguments(%s)' % (self.arguments_w,)
            else:
                return 'Arguments(%s, %s)' % (self.arguments_w, self.kwds_w)
        else:
            return 'Arguments(%s, %s, %s)' % (self.arguments_w,
                                              self.kwds_w,
                                              self.w_stararg)

    ###  Manipulation  ###

    def unpack(self):
        "Return a ([w1,w2...], {'kw':w3...}) pair."
        # --- unpack the * argument now ---
        if self.w_stararg is not None:
            self.arguments_w += self.space.unpackiterable(self.w_stararg)
            self.w_stararg = None
        # --- unpack the ** argument now ---
        if self.kwds_w is None:
            self.kwds_w = {}
        if self.w_starstararg is not None:
            space = self.space
            w_starstararg = self.w_starstararg
            # maybe we could allow general mappings?
            if not space.is_true(space.isinstance(w_starstararg, space.w_dict)):
                raise OperationError(space.w_TypeError,
                                     space.wrap("argument after ** must be "
                                                "a dictionary"))
            # don't change the original yet,
            # in case something goes wrong               
            d = self.kwds_w.copy()
            for w_key in space.unpackiterable(w_starstararg):
                try:
                    key = space.str_w(w_key)
                except OperationError:
                    raise OperationError(space.w_TypeError,
                                         space.wrap("keywords must be strings"))
                if key in d:
                    raise OperationError(self.space.w_TypeError,
                                         self.space.wrap("got multiple values "
                                                         "for keyword argument "
                                                         "'%s'" % key))
                d[key] = space.getitem(w_starstararg, w_key)
            self.kwds_w = d
            self.w_starstararg = None
        return self.arguments_w, self.kwds_w

    def has_keywords(self):
        return bool(self.kwds_w) or (self.w_starstararg is not None and
                                     self.space.is_true(self.w_starstararg))

    def fixedunpack(self, argcount):
        """The simplest argument parsing: get the 'argcount' arguments,
        or raise a real ValueError if the length is wrong."""
        if self.has_keywords():
            raise ValueError, "no keyword arguments expected"
        if len(self.arguments_w) > argcount:
            raise ValueError, "too many arguments (%d expected)" % argcount
        if self.w_stararg is not None:
            self.arguments_w += self.space.unpackiterable(self.w_stararg,
                                             argcount - len(self.arguments_w))
            self.w_stararg = None
        elif len(self.arguments_w) < argcount:
            raise ValueError, "not enough arguments (%d expected)" % argcount
        return self.arguments_w

    def firstarg(self):
        "Return the first argument for inspection."
        if self.arguments_w:
            return self.arguments_w[0]
        if self.w_stararg is None:
            return None
        w_iter = self.space.iter(self.w_stararg)
        try:
            return self.space.next(w_iter)
        except OperationError, e:
            if not e.match(self.space, self.space.w_StopIteration):
                raise
            return None

    ###  Parsing for function calls  ###

    def _unpack_stararg(self):
        space = self.space
        # If w_stararg is not exactly a tuple, unpack it now:
        # self.match_signature() assumes that it can use it directly for
        # a matching *arg in the callee's signature.
        if self.w_stararg is not None:
            if not space.is_w(space.type(self.w_stararg), space.w_tuple):
                self.unpack()

    def parse(self, fnname, signature, defaults_w=[]):
        """Parse args and kwargs to initialize a frame
        according to the signature of code object.
        """
        self._unpack_stararg()
        try:
            return self.match_signature(signature, defaults_w)
        except ArgErr, e:
            raise OperationError(self.space.w_TypeError,
                                 self.space.wrap(e.getmsg(self, fnname)))

    def match_signature(self, signature, defaults_w=[]):
        """Parse args and kwargs according to the signature of a code object,
        or raise an ArgErr in case of failure.
        """
        argnames, varargname, kwargname = signature
        #
        #   args_w = list of the normal actual parameters, wrapped
        #   kwds_w = real dictionary {'keyword': wrapped parameter}
        #   argnames = list of formal parameter names
        #   scope_w = resulting list of wrapped values
        #
        co_argcount = len(argnames) # expected formal arguments, without */**
        if self.w_stararg is not None:
            # There is a case where we don't have to unpack() a w_stararg:
            # if it matches exactly a *arg in the signature.
            if len(self.arguments_w) == co_argcount and varargname is not None:
                pass
            else:
                self.unpack()   # sets self.w_stararg to None
        # always unpack the ** arguments
        if self.w_starstararg is not None:
            self.unpack()

        args_w = self.arguments_w
        kwds_w = self.kwds_w

        # put as many positional input arguments into place as available
        scope_w = args_w[:co_argcount]
        input_argcount = len(scope_w)

        # check that no keyword argument conflicts with these
        # note that for this purpose we ignore the first blind_arguments,
        # which were put into place by prepend().  This way, keywords do
        # not conflict with the hidden extra argument bound by methods.
        if kwds_w and input_argcount > self.blind_arguments:
            for name in argnames[self.blind_arguments:input_argcount]:
                if name in kwds_w:
                    raise ArgErrMultipleValues(name)

        remainingkwds_w = self.kwds_w
        missing = 0
        if input_argcount < co_argcount:
            if remainingkwds_w is None:
                remainingkwds_w = {}
            else:
                remainingkwds_w = remainingkwds_w.copy()            
            # not enough args, fill in kwargs or defaults if exists
            def_first = co_argcount - len(defaults_w)
            for i in range(input_argcount, co_argcount):
                name = argnames[i]
                if name in remainingkwds_w:
                    scope_w.append(remainingkwds_w[name])
                    del remainingkwds_w[name]
                elif i >= def_first:
                    scope_w.append(defaults_w[i-def_first])
                else:
                    # error: not enough arguments.  Don't signal it immediately
                    # because it might be related to a problem with */** or
                    # keyword arguments, which will be checked for below.
                    missing += 1

        # collect extra positional arguments into the *vararg
        if varargname is not None:
            if self.w_stararg is None:   # common case
                if len(args_w) > co_argcount:  # check required by rpython
                    starargs_w = args_w[co_argcount:]
                else:
                    starargs_w = []
                scope_w.append(self.space.newtuple(starargs_w))
            else:      # shortcut for the non-unpack() case above
                scope_w.append(self.w_stararg)
        elif len(args_w) > co_argcount:
            raise ArgErrCount(signature, defaults_w, 0)

        # collect extra keyword arguments into the **kwarg
        if kwargname is not None:
            w_kwds = self.space.newdict([])
            if remainingkwds_w:
                for key, w_value in remainingkwds_w.items():
                    self.space.setitem(w_kwds, self.space.wrap(key), w_value)
            scope_w.append(w_kwds)
        elif remainingkwds_w:
            raise ArgErrUnknownKwds(remainingkwds_w)

        if missing:
            raise ArgErrCount(signature, defaults_w, missing)
        return scope_w

    ### Argument <-> list of w_objects together with "shape" information

    def _rawshape(self, nextra=0):
        shape_cnt  = len(self.arguments_w)+nextra        # Number of positional args
        if self.kwds_w:
            shape_keys = self.kwds_w.keys()           # List of keywords (strings)
        else:
            shape_keys = []
        shape_star = self.w_stararg is not None   # Flag: presence of *arg
        shape_stst = self.w_starstararg is not None # Flag: presence of **kwds
        shape_keys.sort()
        return shape_cnt, tuple(shape_keys), shape_star, shape_stst # shape_keys are sorted

    def flatten(self):
        shape_cnt, shape_keys, shape_star, shape_stst = self._rawshape()
        data_w = self.arguments_w + [self.kwds_w[key] for key in shape_keys]
        if shape_star:
            data_w.append(self.w_stararg)
        if shape_stst:
            data_w.append(self.w_starstararg)
        return (shape_cnt, shape_keys, shape_star, shape_stst), data_w

def rawshape(args, nextra=0):
    return args._rawshape(nextra)


#
# ArgErr family of exceptions raised in case of argument mismatch.
# We try to give error messages following CPython's, which are very informative.
#

class ArgErr(Exception):
    
    def getmsg(self, args, fnname):
        raise NotImplementedError

class ArgErrCount(ArgErr):

    def __init__(self, signature, defaults_w, missing_args):
        self.signature    = signature
        self.defaults_w   = defaults_w
        self.missing_args = missing_args

    def getmsg(self, args, fnname):
        argnames, varargname, kwargname = self.signature
        args_w, kwds_w = args.unpack()
        if kwargname is not None or (kwds_w and self.defaults_w):
            msg2 = "non-keyword "
            if self.missing_args:
                required_args = len(argnames) - len(self.defaults_w)
                nargs = required_args - self.missing_args
            else:
                nargs = len(args_w)
        else:
            msg2 = ""
            nargs = len(args_w) + len(kwds_w)
        n = len(argnames)
        if n == 0:
            msg = "%s() takes no %sargument (%d given)" % (
                fnname, 
                msg2,
                nargs)
        else:
            defcount = len(self.defaults_w)
            if defcount == 0 and varargname is None:
                msg1 = "exactly"
            elif not self.missing_args:
                msg1 = "at most"
            else:
                msg1 = "at least"
                n -= defcount
                if not kwds_w:  # msg "f() takes at least X non-keyword args"
                    msg2 = ""   # is confusing if no kwd arg actually provided
            if n == 1:
                plural = ""
            else:
                plural = "s"
            msg = "%s() takes %s %d %sargument%s (%d given)" % (
                fnname,
                msg1,
                n,
                msg2,
                plural,
                nargs)
        return msg

class ArgErrMultipleValues(ArgErr):

    def __init__(self, argname):
        self.argname = argname

    def getmsg(self, args, fnname):
        msg = "%s() got multiple values for keyword argument '%s'" % (
            fnname,
            self.argname)
        return msg

class ArgErrUnknownKwds(ArgErr):

    def __init__(self, kwds_w):
        self.kwds_w = kwds_w

    def getmsg(self, args, fnname):
        kwds_w = self.kwds_w
        if len(kwds_w) == 1:
            msg = "%s() got an unexpected keyword argument '%s'" % (
                fnname,
                kwds_w.keys()[0])
        else:
            msg = "%s() got %d unexpected keyword arguments" % (
                fnname,
                len(kwds_w))
        return msg
