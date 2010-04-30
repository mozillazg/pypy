from pypy.objspace.flow.model import Variable, SpaceOperation


DEFAULT_OPNAMES_REQUIRING_LIVENESS = set([
    ])

def compute_liveness(graph, opnames_requiring_liveness=
                                DEFAULT_OPNAMES_REQUIRING_LIVENESS):
    for block in graph.iterblocks():
        alive = set()
        for link in block.exits:
            for v in link.args:
                alive.add(v)
        if isinstance(block.exitswitch, tuple):
            for v in block.exitswitch[1:]:
                alive.add(v)
        else:
            alive.add(v)
        for i in range(len(block.operations)-1, -1, -1):
            op = block.operations[i]
            try:
                alive.remove(op.result)
            except KeyError:
                pass
            if op.opname in opnames_requiring_liveness:
                livevars = [v for v in alive if isinstance(v, Variable)]
                block.operations.insert(i, SpaceOperation('-live-', livevars,
                                                          None))
            for v in op.args:
                alive.add(v)
