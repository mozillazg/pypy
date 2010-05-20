from pypy.jit.codewriter.flatten import Register, ListOfKind, Label, TLabel
from pypy.jit.codewriter.jitcode import SwitchDictDescr


# Some instructions require liveness information (the ones that can end up
# in generate_guard() in pyjitpl.py).  This is done by putting special
# space operations called '-live-' in the graph.  They turn into '-live-'
# operation in the ssarepr.  Then this module expands the arguments of
# the '-live-' operations to also include all values that are alive at
# this point: more precisely, all values that are created before the
# '-live-' operation and that are needed afterwards, with the exception
# of the values that are needed only in the very next instruction.  These
# are not considered alive any more.  You can force them to be alive by
# putting them as args of the '-live-' operation in the first place.

# For this to work properly, a special operation called '---' must be
# used to mark unreachable places (e.g. just after a 'goto').

# ____________________________________________________________

def compute_liveness(ssarepr):
    label2alive = {}
    while _compute_liveness_must_continue(ssarepr, label2alive):
        pass

def _compute_liveness_must_continue(ssarepr, label2alive):
    alive = set()
    prevalive = None
    must_continue = False

    for i in range(len(ssarepr.insns)-1, -1, -1):
        insn = ssarepr.insns[i]

        if isinstance(insn[0], Label):
            alive_at_point = label2alive.setdefault(insn[0].name, set())
            prevlength = len(alive_at_point)
            alive_at_point.update(alive)
            if prevlength != len(alive_at_point):
                must_continue = True
            prevalive = None
            continue

        if insn[0] == '-live-':
            assert prevalive is not None
            for x in insn[1:]:
                prevalive.discard(x)
            ssarepr.insns[i] = insn + tuple(prevalive)
            prevalive = None
            continue

        if insn[0] == '---':
            alive = set()
            prevalive = None
            continue

        args = insn[1:]
        #
        if len(args) >= 2 and args[-2] == '->':
            reg = args[-1]
            assert isinstance(reg, Register)
            alive.discard(reg)
            args = args[:-2]
        #
        prevalive = alive.copy()
        #
        for x in args:
            if isinstance(x, Register):
                alive.add(x)
            elif isinstance(x, ListOfKind):
                alive.update(x)
            elif isinstance(x, TLabel):
                alive_at_point = label2alive.get(x.name, ())
                alive.update(alive_at_point)
            elif isinstance(x, SwitchDictDescr):
                for key, label in x._labels:
                    alive_at_point = label2alive.get(label.name, ())
                    alive.update(alive_at_point)

    return must_continue
