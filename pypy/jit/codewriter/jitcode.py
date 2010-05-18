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

    def enumerate_live_vars(self, pc, callback, arg,
                            registers_i, registers_r, registers_f):
        # 'pc' gives a position in this bytecode.  This invokes
        # 'callback' for each variable that is live across the
        # instruction which ends at 'pc'.  (It excludes the arguments
        # of that instruction which are no longer used afterwards, and
        # excludes the return value of that instruction.)  More precisely,
        # this invokes 'callback(arg, box, index)' where 'box' comes from one
        # of the three lists of registers and 'index' is 0, 1, 2...
        # If the callback returns a box, then it is stored back.
        if not we_are_translated() and pc not in self.liveness:
            self._missing_liveness(pc)
        live_i, live_r, live_f = self.liveness[pc]    # XXX compactify!!
        index = 0
        for c in live_i:
            newbox = callback(arg, registers_i[ord(c)], index)
            index += 1
            if newbox is not None:
                registers_i[ord(c)] = newbox
        for c in live_r:
            newbox = callback(arg, registers_r[ord(c)], index)
            index += 1
            if newbox is not None:
                registers_r[ord(c)] = newbox
        for c in live_f:
            newbox = callback(arg, registers_f[ord(c)], index)
            index += 1
            if newbox is not None:
                registers_f[ord(c)] = newbox
        return index
    enumerate_live_vars._annspecialcase_ = 'specialize:arg(2)'

    def _live_vars(self, pc):
        # for testing only
        class Names:
            def __init__(self, kind):
                self.kind = kind
            def __getitem__(self, index):
                return '%%%s%d' % (self.kind, index)
        def callback(lst, reg, index):
            lst.append(reg)
        lst = []
        self.enumerate_live_vars(pc, callback, lst,
                                 Names('i'), Names('r'), Names('f'))
        lst.sort()
        return ' '.join(lst)

    def _missing_liveness(self, pc):
        raise MissingLiveness("missing liveness[%d]\n%s" % (pc, self.dump()))

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
