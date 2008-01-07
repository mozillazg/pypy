import sys
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
        # Pending label targets to fix: [(label, index-in-co_code-to-fix, abs)]
        self.pending_label_fixes = []

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
    # Labels and jumps

    def newBlock(self):
        """This really returns a new label, initially not pointing anywhere."""
        return Label()

    def nextBlock(self, label):
        if label.position >= 0:
            raise InternalCompilerError("Label target already seen")
        label.position = len(self.co_code)

    def emitop_block(self, opname, label):
        absolute = opname in self.hasjabs
        target = label.position
        if target < 0:     # unknown yet
            i = len(self.co_code)
            self.pending_label_fixes.append((label, i, absolute))
            target = 0xFFFF
        else:
            if not absolute:
                # if the target was already seen, it must be backward,
                # which is forbidden for these instructions
                raise InternalCompilerError("%s cannot do a back jump" %
                                            (opname,))
        self.emitop_int(opname, target)

    hasjrel = {}
    for i in pythonopcode.hasjrel:
        hasjrel[pythonopcode.opname[i]] = True
    hasjabs = {}
    for i in pythonopcode.hasjabs:
        hasjabs[pythonopcode.opname[i]] = True
    del i

    # ____________________________________________________________

    def getCode(self):
        self.fixLabelTargets()
        self.computeStackDepth()
        return self.newCodeObject()

    def _setdepth(self, i, stackdepth):
        if stackdepth < 0:
            raise InternalCompilerError("negative stack depth")
        depths = self._stackdepths
        previous_value = depths[i]
        if previous_value < 0:
            if i <= self._stackdepth_seen_until:
                raise InternalCompilerError("back jump to code that is "
                                            "otherwise not reachable")
            depths[i] = stackdepth
        else:
            if previous_value != stackdepth:
                raise InternalCompilerError("inconsistent stack depth")

    def computeStackDepth(self):
        UNREACHABLE = -1
        co_code = self.co_code
        self._stackdepths = [UNREACHABLE] * len(co_code)
        self._stackdepths[0] = 0
        just_loaded_const = None
        consts_w = self.getConsts()
        largestsize = 0
        i = 0

        while i < len(co_code):
            curstackdepth = self._stackdepths[i]
            if curstackdepth > largestsize:
                largestsize = curstackdepth
            self._stackdepth_seen_until = i

            # decode the next instruction
            opcode = ord(co_code[i])
            if opcode >= pythonopcode.HAVE_ARGUMENT:
                oparg = ord(co_code[i+1]) | (ord(co_code[i+2]) << 8)
                i += 3
                if opcode == pythonopcode.opmap['EXTENDED_ARG']:
                    opcode = ord(co_code[i])
                    assert opcode >= pythonopcode.HAVE_ARGUMENT
                    oparg = ((oparg << 16) |
                             ord(co_code[i+1]) | (ord(co_code[i+2]) << 8))
                    i += 3
            else:
                oparg = sys.maxint
                i += 1

            if curstackdepth == UNREACHABLE:
                just_loaded_const = None
                continue    # ignore unreachable instructions

            if opcode in DEPTH_OP_EFFECT_ALONG_JUMP:
                if opcode in pythonopcode.hasjabs:
                    target_i = oparg
                else:
                    target_i = i + oparg
                effect = DEPTH_OP_EFFECT_ALONG_JUMP[opcode]
                self._setdepth(target_i, curstackdepth + effect)

            try:
                tracker = DEPTH_OP_TRACKER[opcode]
            except KeyError:
                pass
            else:
                if opcode == pythonopcode.opmap['MAKE_CLOSURE']:
                    # only supports "LOAD_CONST co / MAKE_CLOSURE n"
                    if just_loaded_const is None:
                        raise InternalCompilerError("MAKE_CLOSURE not "
                                                    "following LOAD_CONST")
                    codeobj = self.space.interp_w(PyCode, just_loaded_const)
                    nfreevars = len(codeobj.co_freevars)
                    effect = - nfreevars - oparg
                else:
                    effect = tracker(oparg)
                self._setdepth(i, curstackdepth + effect)

            if opcode == pythonopcode.opmap['LOAD_CONST']:
                just_loaded_const = consts_w[oparg]
            else:
                just_loaded_const = None

        self.stacksize = largestsize

    def fixLabelTargets(self):
        for label, i, absolute in self.pending_label_fixes:
            target = label.position
            if target < 0:
                raise InternalCompilerError("Label target not found")
            if not absolute:
                target = target - (i+3)   # relative jump
                if target < 0:
                    raise InternalCompilerError("Unexpected backward jump")
            if target > 0xFFFF:
                # CPython has the same limitation, for the same practical
                # reason
                msg = "function too large (bytecode would jump too far away)"
                space = self.space
                raise OperationError(space.w_SystemError, space.wrap(msg))
            self.co_code[i+1] = chr(target & 0xFF)
            self.co_code[i+2] = chr(target >> 8)

    def newCodeObject(self):
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

# ____________________________________________________________

class Label(object):
    position = -1

# ____________________________________________________________
# Stack depth tracking

def depth_UNPACK_SEQUENCE(count):
    return count-1
def depth_BUILD_TUPLE(count):
    return -count+1
def depth_BUILD_LIST(count):
    return -count+1
def depth_CALL_FUNCTION(argc):
    hi = argc//256
    lo = argc%256
    return -(lo + hi * 2)
def depth_CALL_FUNCTION_VAR(argc):
    return depth_CALL_FUNCTION(argc)-1
def depth_CALL_FUNCTION_KW(argc):
    return depth_CALL_FUNCTION(argc)-1
def depth_CALL_FUNCTION_VAR_KW(argc):
    return depth_CALL_FUNCTION(argc)-2
def depth_CALL_METHOD(argc):
    return -argc-1
def depth_CALL_LIKELY_BUILTIN(argc):
    nargs = argc & 0xFF
    return -nargs+1
def depth_MAKE_FUNCTION(argc):
    return -argc
def depth_MAKE_CLOSURE(argc):
    raise InternalCompilerError("must special-case this in order to account"
                                " for the free variables")
def depth_BUILD_SLICE(argc):
    if argc == 2:
        return -1
    elif argc == 3:
        return -2
    assert False, 'Unexpected argument %s to depth_BUILD_SLICE' % argc
    
def depth_DUP_TOPX(argc):
    return argc

def setup_stack_depth_tracker():
    effect = {
        'STOP_CODE': 0,
        'NOP': 0,
        'EXTENDED_ARG': 0,
        'POP_TOP': -1,
        'DUP_TOP': 1,
        'SLICE+0': 0,
        'SLICE+1': -1,
        'SLICE+2': -1,
        'SLICE+3': -2,
        'STORE_SLICE+0': -1,
        'STORE_SLICE+1': -2,
        'STORE_SLICE+2': -2,
        'STORE_SLICE+3': -3,
        'DELETE_SLICE+0': -1,
        'DELETE_SLICE+1': -2,
        'DELETE_SLICE+2': -2,
        'DELETE_SLICE+3': -3,
        'STORE_SUBSCR': -3,
        'DELETE_SUBSCR': -2,
        'PRINT_EXPR': -1,
        'PRINT_ITEM': -1,
        'PRINT_ITEM_TO': -2,
        'PRINT_NEWLINE': 0,
        'PRINT_NEWLINE_TO': -1,
        'YIELD_VALUE': -1,
        'EXEC_STMT': -3,
        'BUILD_CLASS': -2,
        'STORE_NAME': -1,
        'DELETE_NAME': 0,
        'STORE_ATTR': -2,
        'DELETE_ATTR': -1,
        'STORE_GLOBAL': -1,
        'DELETE_GLOBAL': 0,
        'STORE_DEREF': -1,
        'BUILD_MAP': 1,
        'COMPARE_OP': -1,
        'STORE_FAST': -1,
        'DELETE_FAST': 0,
        'IMPORT_STAR': -1,
        'IMPORT_NAME': 0,
        'IMPORT_FROM': 1,
        'LOAD_ATTR': 0, # unlike other loads
        'GET_ITER': 0,
        'FOR_ITER': 1,
        'BREAK_LOOP': 0,
        'CONTINUE_LOOP': 0,
        'POP_BLOCK': 0,
        'END_FINALLY': -3,
        'WITH_CLEANUP': -1,
        'LOOKUP_METHOD': 1,
        'LIST_APPEND': -2,
        }
    # use pattern match
    patterns = [
        ('ROT_', 0),
        ('UNARY_', 0),
        ('BINARY_', -1),
        ('INPLACE_', -1),
        ('LOAD_', 1),
        ('SETUP_', 0),
        ('JUMP_IF_', 0),
        ]

    def gettracker(opname):
        # first look for an explicit tracker
        try:
            return globals()['depth_' + opname]
        except KeyError:
            pass
        # then look for an explicit constant effect
        try:
            delta = effect[opname]
        except KeyError:
            # then do pattern matching
            for pat, delta in patterns:
                if opname.startswith(pat):
                    break
            else:
                raise InternalCompilerError("no stack effect registered for "
                                            + opname)
        def tracker(argc):
            return delta
        return tracker

    effect_along_jump = {
        'JUMP_FORWARD': 0,
        'JUMP_ABSOLUTE': 0,
        'JUMP_IF_TRUE': 0,
        'JUMP_IF_FALSE': 0,
        'FOR_ITER': -1,
        'SETUP_LOOP': 0,
        'SETUP_EXCEPT': 3,
        'SETUP_FINALLY': 3,
        }
    def geteffect_jump(opname):
        try:
            return effect_along_jump[opname]
        except KeyError:
            raise InternalCompilerError("no stack effect registered for "
                                        "the branch of " + opname)

    for opname, opcode in pythonopcode.opmap.items():
        if opname in ops_interrupt_unconditionally:
            continue
        if opname not in ops_jump_unconditionally:
            # the effect on the stack depth when execution goes from
            # this instruction to the next one
            DEPTH_OP_TRACKER[opcode] = gettracker(opname)
        if opname in ops_jumps:
            DEPTH_OP_EFFECT_ALONG_JUMP[opcode] = geteffect_jump(opname)


ops_interrupt_unconditionally = ('RETURN_VALUE', 'RAISE_VARARGS',
                                 'CONTINUE_LOOP', 'BREAK_LOOP')
ops_jump_unconditionally = ('JUMP_ABSOLUTE', 'JUMP_FORWARD')
ops_jumps = list(PyFlowGraph.hasjrel) + list(PyFlowGraph.hasjabs)

DEPTH_OP_TRACKER = {}
DEPTH_OP_EFFECT_ALONG_JUMP = {}
setup_stack_depth_tracker()
