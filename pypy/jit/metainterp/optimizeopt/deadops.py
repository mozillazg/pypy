
from pypy.jit.metainterp.history import rop

def remove_dead_ops(loop):
    newops = []
    seen = {}
    for i in range(len(loop.operations) -1, -1, -1):
        op = loop.operations[i]
        # XXX SAME_AS is required for crazy stuff that unroll does, which
        #     makes dead ops sometime alive
        if (op.opnum not in [rop.LABEL, rop.JUMP, rop.SAME_AS]
            and op.has_no_side_effect()
            and op.result not in seen):
            continue
        for arg in op.getarglist():
            seen[arg] = None
        if op.getfailargs():
            for arg in op.getfailargs():
                seen[arg] = None
        newops.append(op)
    newops.reverse()
    loop.operations[:] = newops
