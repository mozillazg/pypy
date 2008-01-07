from pypy.interpreter.astcompiler.consts \
     import CO_OPTIMIZED, CO_NEWLOCALS, CO_VARARGS, CO_VARKEYWORDS
from pypy.interpreter.pycode import PyCode
from pypy.tool import stdlib_opcode as pythonopcode
from pypy.interpreter.error import OperationError


class InternalCompilerError(Exception):
    """Something went wrong in the ast compiler."""


class PyFlowGraph(object):

    def __init__(self, space, name, filename, argnames=None,
                 optimized=0, klass=0, newlocals=0):
        self.space = space
        if argnames is None:
            argnames = []
        self.name = name
        self.filename = filename
        self.docstring = space.w_None
        self.argcount = len(argnames)
        self.klass = klass
        self.flags = 0
        if optimized:
            self.flags |= CO_OPTIMIZED
        if newlocals:
            self.flags |= CO_NEWLOCALS

        # XXX we need to build app-level dict here, bleh
        self.w_consts = space.newdict()
        #self.const_list = []
        self.names = []
        # Free variables found by the symbol table scan, including
        # variables used only in nested scopes, are included here.
        self.freevars = []
        self.cellvars = []
        # The closure list is used to track the order of cell
        # variables and free variables in the resulting code object.
        # The offsets used by LOAD_CLOSURE/LOAD_DEREF refer to both
        # kinds of variables.
        self.closure = []
        self.varnames = list(argnames)
        # The bytecode we are building, as a list of characters
        self.co_code = []

    def setDocstring(self, doc):
        self.docstring = doc

    def setFlag(self, flag):
        self.flags = self.flags | flag
        if flag == CO_VARARGS:
            self.argcount = self.argcount - 1

    def checkFlag(self, flag):
        if self.flags & flag:
            return 1

    def setFreeVars(self, names):
        self.freevars = list(names)

    def setCellVars(self, names):
        self.cellvars = names

    # ____________________________________________________________
    # Simple instructions

    def emit(self, opname):
        self.co_code.append(chr(pythonopcode.opmap[opname]))

    def emitop_extended_arg(self, intval):
        assert intval <= 0x7FFFFFFF
        self.emit('EXTENDED_ARG')
        self.co_code.append(chr((intval >> 16) & 0xFF))
        self.co_code.append(chr((intval >> 24) & 0xFF))
        return intval & 0xFFFF
    emitop_extended_arg._dont_inline_ = True

    def emitop_int(self, opname, intval):
        assert intval >= 0
        if opname == "SET_LINENO":
            return  # XXX
        if intval > 0xFFFF:
            intval = self.emitop_extended_arg(intval)
        self.emit(opname)
        self.co_code.append(chr(intval & 0xFF))
        self.co_code.append(chr(intval >> 8))

    # ____________________________________________________________
    # Instructions with an object argument (LOAD_CONST)

    def emitop_obj(self, opname, w_obj):
        index = self._lookupConst(w_obj, self.w_consts)
        self.emitop_int(opname, index)

    def _lookupConst(self, w_obj, w_dict):
        space = self.space
        w_obj_type = space.type(w_obj)
        w_key = space.newtuple([w_obj, w_obj_type])
        try:
            w_result = space.getitem(w_dict, w_key)
        except OperationError, operr:
            if not operr.match(space, space.w_KeyError):
                raise
            w_result = space.len(w_dict)
            space.setitem(w_dict, w_key, w_result)
        return space.int_w(w_result)

    # ____________________________________________________________
    # Instructions with a name argument

    def emitop_name(self, opname, name):
        conv = self._converters[opname]
        index = conv(self, name)
        self.emitop_int(opname, index)

    def _lookupName(self, name, list):
        """Return index of name in list, appending if necessary
        """
        # XXX use dicts instead of lists
        assert isinstance(name, str)
        for i in range(len(list)):
            if list[i] == name:
                return i
        end = len(list)
        list.append(name)
        return end

    def _convert_LOAD_FAST(self, arg):
        self._lookupName(arg, self.names)
        return self._lookupName(arg, self.varnames)
    _convert_STORE_FAST = _convert_LOAD_FAST
    _convert_DELETE_FAST = _convert_LOAD_FAST

    def _convert_NAME(self, arg):
        return self._lookupName(arg, self.names)
    _convert_LOAD_NAME = _convert_NAME
    _convert_STORE_NAME = _convert_NAME
    _convert_DELETE_NAME = _convert_NAME
    _convert_IMPORT_NAME = _convert_NAME
    _convert_IMPORT_FROM = _convert_NAME
    _convert_STORE_ATTR = _convert_NAME
    _convert_LOAD_ATTR = _convert_NAME
    _convert_DELETE_ATTR = _convert_NAME
    _convert_LOAD_GLOBAL = _convert_NAME
    _convert_STORE_GLOBAL = _convert_NAME
    _convert_DELETE_GLOBAL = _convert_NAME
    _convert_LOOKUP_METHOD = _convert_NAME

    def _convert_DEREF(self, arg):
        self._lookupName(arg, self.names)
        return self._lookupName(arg, self.closure)
    _convert_LOAD_DEREF = _convert_DEREF
    _convert_STORE_DEREF = _convert_DEREF

    def _convert_LOAD_CLOSURE(self, arg):
        return self._lookupName(arg, self.closure)

    _cmp = list(pythonopcode.cmp_op)
    def _convert_COMPARE_OP(self, arg):
        return self._cmp.index(arg)

    _converters = {}
    for name, obj in locals().items():
        if name[:9] == "_convert_":
            opname = name[9:]
            _converters[opname] = obj
    del name, obj, opname

    # ____________________________________________________________

    def getCode(self):
        self.stacksize = 20  # XXX!
        if (self.flags & CO_NEWLOCALS) == 0:
            nlocals = 0
        else:
            nlocals = len(self.varnames)
        argcount = self.argcount
        if self.flags & CO_VARKEYWORDS:
            argcount = argcount - 1
        return PyCode( self.space, argcount, nlocals,
                       self.stacksize, self.flags,
                       ''.join(self.co_code),
                       self.getConsts(),
                       self.names,
                       self.varnames,
                       self.filename, self.name,
                       1,     # XXX! self.firstline,
                       "",    # XXX! self.lnotab.getTable(),
                       self.freevars,
                       self.cellvars
                       )

    def getConsts(self):
        """Return a tuple for the const slot of the code object
        """
        space = self.space
        keys_w = space.unpackiterable(self.w_consts)
        l_w = [None] * len(keys_w)
        for w_key in keys_w:
            index = space.int_w(space.getitem(self.w_consts, w_key))
            w_v = space.unpacktuple(w_key)[0]
            l_w[index] = w_v
        return l_w
