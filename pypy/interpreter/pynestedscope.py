from pypy.interpreter.pyfastscope import PyFastScopeFrame, UNDEFINED


class Cell(object):
    "A simple container for a wrapped value."
    
    def __init__(self, w_value=UNDEFINED):
        self.w_value = w_value

    def clone(self):
        return self.__class__(self.w_value)

    def empty(self):
        return self.w_value is UNDEFINED

    def get(self):
        if self.w_value is UNDEFINED:
            raise ValueError, "get() from an empty cell"
        return self.w_value

    def set(self, w_value):
        self.w_value = w_value

    def delete(self):
        if self.w_value is UNDEFINED:
            raise ValueError, "delete() on an empty cell"
        self.w_value = UNDEFINED

    def __repr__(self):
        """ representation for debugging purposes """
        if self.w_value is UNDEFINED:
            content = ""
        else:
            content = repr(self.w_value)
        return "<%s(%s) at 0x%x>" % (self.__class__.__name__,
                                     content, id(self))


class PyNestedScopeFrame(PyFastScopeFrame):
    """This class enhances a standard frame with nested scope abilities,
    i.e. handling of cell/free variables."""

    def __init__(self, space, code):
        PyFastScopeFrame.__init__(self, space, code)
        ncellvars = len(code.co_cellvars)
        nfreevars = len(code.co_freevars)
        self.cells = [None] * (ncellvars + nfreevars)

    def fast2locals(self):
        PyFastScopeFrame.fast2locals(self)
        freevarnames = self.bytecode.co_cellvars + self.bytecode.co_freevars
        for name, cell in zip(freevarnames, self.cells):
            try:
                w_value = cell.get()
            except ValueError:
                pass
            else:
                w_name = self.space.wrap(name)
                self.space.setitem(self.w_locals, w_name, w_value)

    def locals2fast(self):
        PyFastScopeFrame.locals2fast(self)
        freevarnames = self.bytecode.co_cellvars + self.bytecode.co_freevars
        for name, cell in zip(freevarnames, self.cells):
            w_name = self.space.wrap(name)
            try:
                w_value = self.space.getitem(self.w_locals, w_name)
            except OperationError, e:
                if not e.match(self.space, self.space.w_KeyError):
                    raise
            else:
                cell.set(w_value)

    def setclosure(self, closure):
        # Cell Vars:
        #     my local variables that are exposed to my inner functions
        # Free Vars:
        #     variables coming from a parent function in which i'm nested
        # 'closure' is a list of Cell instances: the received free vars.
        code = self.bytecode
        ncellvars = len(code.co_cellvars)
        nfreevars = len(code.co_freevars)
        if ncellvars:
            # the first few cell vars could shadow already-set arguments,
            # in the same order as they appear in co_varnames
            nargvars = code.getargcount()
            argvars  = code.co_varnames
            cellvars = code.co_cellvars
            next     = 0
            nextname = cellvars[0]
            for i in range(nargvars):
                if argvars[i] == nextname:
                    # argument i has the same name as the next cell var
                    w_value = self.locals_w[i]
                    self.cells[next] = Cell(w_value)
                    next += 1
                    try:
                        nextname = cellvars[next]
                    except IndexError:
                        break   # all cell vars initialized this way
            else:
                # the remaining cell vars are empty
                for i in range(next, ncellvars):
                    self.cells[i] = Cell()
        # following the cell vars are the free vars, copied from 'closure'
        if closure is None:
            closure = []
        if len(closure) != nfreevars:
            raise TypeError, ("%d free variables expected, got %d" %
                              (nfreevars, len(closure)))   # internal error
        self.cells[ncellvars:] = closure

    def getfreevarname(self, index):
        freevarnames = self.bytecode.co_cellvars + self.bytecode.co_freevars
        return freevarnames[index]

    def iscellvar(self, index):
        # is the variable given by index a cell or a free var?
        return index < len(self.bytecode.co_cellvars)

    ### extra opcodes ###

    def LOAD_CLOSURE(f, varindex):
        # nested scopes: access the cell object
        cell = f.cells[varindex]
        assert cell is not None, "setclosure() was not called"
        w_value = f.space.wrap(cell)
        f.valuestack.push(w_value)

    def LOAD_DEREF(f, varindex):
        # nested scopes: access a variable through its cell object
        cell = f.cells[varindex]
        try:
            w_value = cell.get()
        except ValueError:
            varname = f.getfreevarname(varindex)
            if f.iscellvar(varindex):
                message = "local variable '%s' referenced before assignment"
                w_exc_type = f.space.w_UnboundLocalError
            else:
                message = ("free variable '%s' referenced before assignment"
                           " in enclosing scope")
                w_exc_type = f.space.w_NameError
            raise OperationError(w_exc_type, f.space.wrap(message % varname))
        else:
            f.valuestack.push(w_value)

    def STORE_DEREF(f, varindex):
        # nested scopes: access a variable through its cell object
        w_newvalue = f.valuestack.pop()
        #try:
        cell = f.cells[varindex]
        #except IndexError:
        #    import pdb; pdb.set_trace()
        #    raise
        cell.set(w_newvalue)

    def MAKE_CLOSURE(f, numdefaults):
        w_codeobj = f.valuestack.pop()
        codeobj = f.space.unwrap(w_codeobj)
        nfreevars = len(codeobj.co_freevars)
        freevars = [f.valuestack.pop() for i in range(nfreevars)]
        freevars.reverse()
        w_freevars = f.space.newtuple(freevars)
        defaultarguments = [f.valuestack.pop() for i in range(numdefaults)]
        defaultarguments.reverse()
        w_defaultarguments = f.space.newtuple(defaultarguments)
        w_func = f.space.newfunction(f.space.unwrap(w_codeobj),
                                     f.w_globals, w_defaultarguments, w_freevars)
        f.valuestack.push(w_func)


PyNestedScopeFrame.setup_dispatch_table()
