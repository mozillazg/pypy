from pypy.objspace.flow.model import Variable, SpaceOperation, c_last_exception


# Some instruction require liveness information (the ones that can end up
# in generate_guard() in pyjitpl.py); jtransform.py prefixes these opnames
# with a 'G_'.  Additionally, boolean and general switches in the flow graph
# will turn in 'goto_if_not_*' operations, which also require liveness info.

# ____________________________________________________________

def compute_liveness(graph, switches_require_liveness=True):
    for block in graph.iterblocks():
        num_operations = len(block.operations)
        alive = set()
        for link in block.exits:
            for v in link.args:
                if (v is not link.last_exception and
                    v is not link.last_exc_value):
                    alive.add(v)
        if switches_require_liveness:
            if len(block.exits) > 1 and block.exitswitch != c_last_exception:
                block.operations.append(_livespaceop(alive))
        if isinstance(block.exitswitch, tuple):
            for v in block.exitswitch[1:]:
                alive.add(v)
        else:
            alive.add(block.exitswitch)
        for i in range(num_operations-1, -1, -1):
            op = block.operations[i]
            try:
                alive.remove(op.result)
            except KeyError:
                pass
            if op.opname.startswith('G_'):
                block.operations.insert(i, _livespaceop(alive))
            for v in op.args:
                alive.add(v)

def _livespaceop(alive):
    livevars = [v for v in alive if isinstance(v, Variable)]
    return SpaceOperation('-live-', livevars, None)
