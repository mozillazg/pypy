# load opcode.py as pythonopcode from our own lib

__all__ = ['opmap', 'opname', 'HAVE_ARGUMENT',
           'hasconst', 'hasname', 'hasjrel', 'hasjabs',
           'haslocal', 'hascompare', 'hasfree', 'cmp_op']

from opcode import (
    opmap as host_opmap, HAVE_ARGUMENT as host_HAVE_ARGUMENT)

def load_opcode():
    import py
    opcode_path = py.path.local(__file__).dirpath().dirpath().dirpath('lib-python/modified-2.5.2/opcode.py')
    d = {}
    execfile(str(opcode_path), d)
    return d

opcode_dict = load_opcode()
del load_opcode

# copy some stuff from opcode.py directly into our globals
for name in __all__:
    if name in opcode_dict:
        globals()[name] = opcode_dict[name]
globals().update(opmap)
SLICE = opmap["SLICE+0"]
STORE_SLICE = opmap["STORE_SLICE+0"]
DELETE_SLICE = opmap["DELETE_SLICE+0"]

def make_method_names(opmap):
    tbl = ['MISSING_OPCODE'] * 256
    for name, index in opmap.items():
        tbl[index] = name.replace('+', '_')
    return tbl

opcode_method_names = make_method_names(opmap)
host_opcode_method_names = make_method_names(host_opmap)
#print (
    #set(enumerate(opcode_method_names)) ^ set(enumerate(host_opcode_method_names))
#)
del make_method_names

# ____________________________________________________________
# RPython-friendly helpers and structures

from pypy.rlib.unroll import unrolling_iterable

def make_opcode_desc(HAVE_ARGUMENT):
    class OpcodeDesc(object):
        def __init__(self, name, index):
            self.name = name
            self.methodname = opcode_method_names[index]
            self.index = index
            self.hasarg = index >= HAVE_ARGUMENT

        def _freeze_(self):
            return True

        def is_enabled(self, space):
            """Check if the opcode should be enabled in the space's configuration.
            (Returns True for all standard opcodes.)"""
            opt = space.config.objspace.opcodes
            return getattr(opt, self.name, True)
        is_enabled._annspecialcase_ = 'specialize:memo'

        # for predictable results, we try to order opcodes most-used-first
        opcodeorder = [124, 125, 100, 105, 1, 131, 116, 111, 106, 83, 23, 93, 113, 25, 95, 64, 112, 66, 102, 110, 60, 92, 62, 120, 68, 87, 32, 136, 4, 103, 24, 63, 18, 65, 15, 55, 121, 3, 101, 22, 12, 80, 86, 135, 126, 90, 140, 104, 2, 33, 20, 108, 107, 31, 134, 132, 88, 30, 133, 130, 137, 141, 61, 122, 11, 40, 74, 73, 51, 96, 21, 42, 56, 85, 82, 89, 142, 77, 78, 79, 91, 76, 97, 57, 19, 43, 84, 50, 41, 99, 53, 26]

        def sortkey(self):
            try:
                i = self.opcodeorder.index(self.index)
            except ValueError:
                i = 1000000
            return i, self.index

        def __cmp__(self, other):
            return (cmp(self.__class__, other.__class__) or
                    cmp(self.sortkey(), other.sortkey()))

    return OpcodeDesc

OpcodeDesc = make_opcode_desc(HAVE_ARGUMENT)
HostOpcodeDesc = make_opcode_desc(host_HAVE_ARGUMENT)

opdescmap = {}

class _baseopcodedesc:
    pass

class opcodedesc(_baseopcodedesc):
    """A namespace mapping OPCODE_NAME to OpcodeDescs."""

class host_opcodedesc(_baseopcodedesc):
    """A namespace mapping OPCODE_NAME to HostOpcodeDescs."""

for name, index in opmap.items():
    desc = OpcodeDesc(name, index)
    setattr(opcodedesc, name, desc)
    opdescmap[index] = desc

for name, index in host_opmap.items():
    desc = HostOpcodeDesc(name, index)
    setattr(host_opcodedesc, name, desc)

lst = opdescmap.values()
lst.sort()
unrolling_opcode_descs = unrolling_iterable(lst)

del name, index, desc, lst
