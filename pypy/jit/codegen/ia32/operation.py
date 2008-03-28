
from pypy.jit.codegen.i386.ri386 import *
from pypy.jit.codegen.model import GenVar
from pypy.rlib.objectmodel import specialize
from pypy.rpython.lltypesystem import lltype

class Operation(GenVar):
    pass

class Op1(Operation):
    def __init__(self, x):
        self.x = x

class Op2(Operation):
    def __init__(self, x, y):
        self.x = x
        self.y = y

class OpIntAdd(Op2):
    opname = "int_add"

    def render(self, allocator, mc):
        p1 = allocator.get_position(self.x)
        p2 = allocator.get_position(self.y)
        mc.ADD(p1, p2)
        allocator.set_position(self, p1)

def setup_opclasses(base):
    d = {}
    for name, value in globals().items():
        if type(value) is type(base) and issubclass(value, base):
            opnames = getattr(value, 'opname', ())
            if isinstance(opnames, str):
                opnames = (opnames,)
            for opname in opnames:
                assert opname not in d
                d[opname] = value
    return d
OPCLASSES1 = setup_opclasses(Op1)
OPCLASSES2 = setup_opclasses(Op2)
del setup_opclasses

@specialize.memo()
def getopclass1(opname):
    try:
        return OPCLASSES1[opname]
    except KeyError:
        raise MissingBackendOperation(opname)

@specialize.memo()
def getopclass2(opname):
    try:
        return OPCLASSES2[opname]
    except KeyError:
        raise MissingBackendOperation(opname)

class OpCall(Operation):
    def __init__(self, sigtoken, gv_fnptr, args_gv):
        self.sigtoken = sigtoken
        self.gv_fnptr = gv_fnptr
        self.args_gv = args_gv

    def render(self, allocator, mc):
        fnptr = self.gv_fnptr
        assert fnptr.is_const
        stack_pos = 0
        for i in range(len(self.args_gv)):
            gv = self.args_gv[i]
            src = allocator.get_position(gv)
            if not isinstance(src, MODRM):
                mc.MOV(mem(esp, stack_pos), src)
            else:
                mc.MOV(eax, src)
                mc.MOV(mem(esp, stack_pos), eax)
            stack_pos += gv.SIZE
        mc.CALL(rel32(fnptr.value))
        allocator.set_position(self, eax)
