
def remove_dead_ops(loop):
    newops = []
    seen = {}
    for i in range(len(loop.operations) -1, -1, -1):
        op = loop.operations[i]
        if op.has_no_side_effect() and op.result not in seen:
            continue
        for arg in op.getarglist():
            seen[arg] = None
        if op.getfailargs():
            for arg in op.getfailargs():
                seen[arg] = None
        newops.append(op)
    newops.reverse()
    loop.operations[:] = newops
