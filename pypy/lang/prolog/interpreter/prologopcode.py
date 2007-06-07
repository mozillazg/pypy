
hasargument = []
hascontinuation = []

opmap = {}
allopcodes = []
opname = [''] * 256
for op in range(256): opname[op] = '<%r>' % (op,)
del op

def def_op(name, op, continuation=False):
    op = ord(op)
    opname[op] = name
    opmap[name] = op
    allopcodes.append(op)
    if continuation:
        hascontinuation.append(op)


def argument_op(name, op, continuation=False):
    assert ord(op) >= HAVE_ARGUMENT
    def_op(name, op, continuation)
    hasargument.append(ord(op))


HAVE_ARGUMENT = 97 # capitals

# term construction
argument_op("PUTCONSTANT", 'c')
argument_op("PUTLOCALVAR", 'l')
argument_op("MAKETERM", 't')

# running
argument_op("CALL_BUILTIN", 'b', True)
argument_op("CLEAR_LOCAL", 'x')
def_op("UNIFY", 'U')
def_op("DYNAMIC_CALL", 'D', True)
argument_op("STATIC_CALL", 's', True)
def_op("CUT", 'C', True)

class OpcodeDesc(object):
    def __init__(self, name, index):
        self.name = name
        self.index = index
        self.hasargument = index >= HAVE_ARGUMENT
        self.hascontinuation = index in hascontinuation

    def _freeze_(self):
        return True

    def __cmp__(self, other):
        return cmp(self.index, other.index)

lst = []


class opcodedesc(object):
    pass

for name, index in opmap.items():
    desc = OpcodeDesc(name, index)
    setattr(opcodedesc, name, desc)
    lst.append(desc)
lst.sort()

from pypy.rlib.unroll import unrolling_iterable

unrolling_opcode_descs = unrolling_iterable(lst)
del lst
