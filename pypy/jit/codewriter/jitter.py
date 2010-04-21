from pypy.rpython.lltypesystem import lltype


def transform_graph(graph):
    """Transform a control flow graph to make it suitable for
    being flattened in a JitCode.
    """
    for block in graph.iterblocks():
        optimize_goto_if_not(block)


def optimize_goto_if_not(block):
    """Replace code like 'v = int_gt(x,y); exitswitch = v'
       with just 'exitswitch = ('int_gt',x,y)'."""
    if len(block.exits) != 2:
        return False
    v = block.exitswitch
    if v.concretetype != lltype.Bool:
        return False
    for link in block.exits:
        if v in link.args:
            return False   # variable escapes to next block
    for op in block.operations[::-1]:
        if v in op.args:
            return False   # variable is also used in cur block
        if v is op.result:
            if op.opname not in ('int_lt', 'int_le', 'int_eq', 'int_ne',
                                 'int_gt', 'int_ge'):
                return False    # not a supported operation
            # ok! optimize this case
            block.operations.remove(op)
            block.exitswitch = (op.opname,) + tuple(op.args)
            return True
    return False
