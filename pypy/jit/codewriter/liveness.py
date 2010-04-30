import re
from pypy.objspace.flow.model import Variable, SpaceOperation


def compile_re(opnames):
    return re.compile('|'.join(opnames))

# List of instruction prefixes that might need the liveness information
# (they are the ones that can end up in generate_guard() in pyjitpl.py).
# Note that the goto_if_not_* operations are not present in the control
# flow graph format; their liveness information is attached by setting
# 'switches_require_liveness' to True.
DEFAULT_OPNAMES_REQUIRING_LIVENESS = [
    'residual_call_',
    ]

# ____________________________________________________________

def compute_liveness(graph,
                     switches_require_liveness = True,
                     opnames_requiring_liveness =
                         compile_re(DEFAULT_OPNAMES_REQUIRING_LIVENESS)):
    if isinstance(opnames_requiring_liveness, list):
        opnames_requiring_liveness = compile_re(opnames_requiring_liveness)
    for block in graph.iterblocks():
        num_operations = len(block.operations)
        alive = set()
        for link in block.exits:
            for v in link.args:
                alive.add(v)
        if switches_require_liveness and len(block.exits) > 1:
            block.operations.append(_livespaceop(alive))
        if isinstance(block.exitswitch, tuple):
            for v in block.exitswitch[1:]:
                alive.add(v)
        else:
            alive.add(v)
        for i in range(num_operations-1, -1, -1):
            op = block.operations[i]
            try:
                alive.remove(op.result)
            except KeyError:
                pass
            if opnames_requiring_liveness.match(op.opname):
                block.operations.insert(i, _livespaceop(alive))
            for v in op.args:
                alive.add(v)

def _livespaceop(alive):
    livevars = [v for v in alive if isinstance(v, Variable)]
    return SpaceOperation('-live-', livevars, None)
