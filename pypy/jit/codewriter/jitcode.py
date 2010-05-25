from pypy.jit.metainterp.history import AbstractDescr
from pypy.rlib.objectmodel import we_are_translated
from pypy.rpython.lltypesystem import llmemory


class JitCode(AbstractDescr):
    _empty_i = []
    _empty_r = []
    _empty_f = []

    def __init__(self, name, fnaddr=None, calldescr=None, called_from=None):
        self.name = name
        self.fnaddr = fnaddr
        self.calldescr = calldescr
        self._called_from = called_from   # debugging
        self._ssarepr     = None          # debugging

    def setup(self, code='', constants_i=[], constants_r=[], constants_f=[],
              num_regs_i=255, num_regs_r=255, num_regs_f=255,
              liveness=None, startpoints=None, alllabels=None):
        self.code = code
        # if the following lists are empty, use a single shared empty list
        self.constants_i = constants_i or self._empty_i
        self.constants_r = constants_r or self._empty_r
        self.constants_f = constants_f or self._empty_f
        # encode the three num_regs into a single integer
        assert num_regs_i < 256 and num_regs_r < 256 and num_regs_f < 256
        self.num_regs_encoded = ((num_regs_i << 16) |
                                 (num_regs_f << 8) |
                                 (num_regs_r << 0))
        self.liveness = liveness
        self._startpoints = startpoints   # debugging
        self._alllabels = alllabels       # debugging

    def get_fnaddr_as_int(self):
        return llmemory.cast_adr_to_int(self.fnaddr)

    def num_regs_i(self):
        return self.num_regs_encoded >> 16

    def num_regs_f(self):
        return (self.num_regs_encoded >> 8) & 0xFF

    def num_regs_r(self):
        return self.num_regs_encoded & 0xFF

    def has_liveness_info(self, pc):
        return pc in self.liveness

    def get_live_vars_info(self, pc):
        # 'pc' gives a position in this bytecode.  This returns an object
        # that describes all variables that are live across the instruction
        # boundary at 'pc'.  To decode the object, use the global functions
        # 'get_register_{count,index}_{i,r,f}()'.
        if not we_are_translated() and pc not in self.liveness:
            self._missing_liveness(pc)
        return self.liveness[pc]    # XXX compactify!!

    def _live_vars(self, pc):
        # for testing only
        info = self.get_live_vars_info(pc)
        lst_i = ['%%i%d' % get_register_index_i(info, index)
                 for index in range(get_register_count_i(info))]
        lst_r = ['%%r%d' % get_register_index_r(info, index)
                 for index in range(get_register_count_r(info))]
        lst_f = ['%%f%d' % get_register_index_f(info, index)
                 for index in range(get_register_count_f(info))]
        return ' '.join(lst_i + lst_r + lst_f)

    def _missing_liveness(self, pc):
        raise MissingLiveness("missing liveness[%d]\n%s" % (pc, self.dump()))

    def follow_jump(self, position):
        """Assuming that 'position' points just after a bytecode
        instruction that ends with a label, follow that label."""
        code = self.code
        position -= 2
        assert position >= 0
        if not we_are_translated():
            assert position in self._alllabels
        labelvalue = ord(code[position]) | (ord(code[position+1])<<8)
        assert labelvalue < len(code)
        return labelvalue

    def dump(self):
        if self._ssarepr is None:
            return '<no dump available>'
        else:
            from pypy.jit.codewriter.format import format_assembler
            return format_assembler(self._ssarepr)

    def __repr__(self):
        return '<JitCode %r>' % self.name

class MissingLiveness(Exception):
    pass


class SwitchDictDescr(AbstractDescr):
    "Get a 'dict' attribute mapping integer values to bytecode positions."

    def __repr__(self):
        dict = getattr(self, 'dict', '?')
        return '<SwitchDictDescr %s>' % (dict,)


def get_register_count_i((live_i, live_r, live_f)):
    return len(live_i)
def get_register_count_r((live_i, live_r, live_f)):
    return len(live_r)
def get_register_count_f((live_i, live_r, live_f)):
    return len(live_f)

def get_register_index_i((live_i, live_r, live_f), index):
    return ord(live_i[index])
def get_register_index_r((live_i, live_r, live_f), index):
    return ord(live_r[index])
def get_register_index_f((live_i, live_r, live_f), index):
    return ord(live_f[index])
