from pypy.interpreter.pyopcode import PyOperationalFrame


UNDEFINED = object()  # marker for undefined local variables


class PyFastScopeFrame(PyOperationalFrame):
    "A PyFrame that knows about fast scopes."

    # this is the class that knows about "fast locals", i.e.
    # the fact that local variables are better represented as an array
    # of values accessed by index (by the LOAD_FAST, STORE_FAST and
    # DELETE_FAST opcodes).

    def __init__(self, space, code):
        PyOperationalFrame.__init__(self, space, code)
        self.locals_w = [UNDEFINED] * code.co_nlocals

    def getlocalvarname(self, index):
        return self.bytecode.co_varnames[index]

    def getlocaldict(self):
        self.fast2locals()
        return self.w_locals

    def setlocaldict(self, w_locals):
        self.w_locals = w_locals
        self.locals2fast()

    def getlocalvar(self, index):
        return self.locals_w[index]

    def setlocalvar(self, index, w_value):
        self.locals_w[index] = w_value

    def fast2locals(self):
        # Copy values from self.locals_w to self.w_locals
        if self.w_locals is None:
            self.w_locals = self.space.newdict([])
        for name, w_value in zip(self.bytecode.co_varnames, self.locals_w):
            if w_value is not UNDEFINED:
                w_name = self.space.wrap(name)
                self.space.setitem(self.w_locals, w_name, w_value)

    def locals2fast(self):
        # Copy values from self.w_locals to self.locals_w
        for i in range(self.bytecode.co_nlocals):
            w_name = self.space.wrap(self.bytecode.co_varnames[i])
            try:
                w_value = self.space.getitem(self.w_locals, w_name)
            except OperationError, e:
                if not e.match(self.space, self.space.w_KeyError):
                    raise
            else:
                self.locals_w[i] = w_value

    ### extra opcodes ###

    def LOAD_FAST(f, varindex):
        # access a local variable directly
        w_value = f.locals_w[varindex]
        if w_value is UNDEFINED:
            varname = f.getlocalvarname(varindex)
            message = "local variable '%s' referenced before assignment" % varname
            raise OperationError(f.space.w_UnboundLocalError, f.space.wrap(message))
        f.valuestack.push(w_value)

    def STORE_FAST(f, varindex):
        try:
            w_newvalue = f.valuestack.pop()
            f.locals_w[varindex] = w_newvalue
        except:
            print "exception: got index error"
            print " varindex:", varindex
            print " len(locals_w)", len(f.locals_w)
            import dis
            print dis.dis(f.bytecode)
            print "co_varnames", f.bytecode.co_varnames
            print "co_nlocals", f.bytecode.co_nlocals
            raise

    def DELETE_FAST(f, varindex):
        w_value = f.locals_w[varindex]
        if f.locals_w[varindex] is UNDEFINED:
            varname = f.getlocalvarname(varindex)
            message = "local variable '%s' referenced before assignment" % varname
            raise OperationError(f.space.w_UnboundLocalError, f.space.wrap(message))
        f.locals_w[varindex] = UNDEFINED


PyFastScopeFrame.setup_dispatch_table()
