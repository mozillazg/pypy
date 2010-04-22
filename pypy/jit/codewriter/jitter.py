from pypy.rpython.lltypesystem import lltype
from pypy.jit.metainterp.history import getkind
from pypy.objspace.flow.model import SpaceOperation


def transform_graph(graph):
    """Transform a control flow graph to make it suitable for
    being flattened in a JitCode.
    """
    for block in graph.iterblocks():
        for i in range(len(block.operations)):
            block.operations[i] = rewrite_operation(block.operations[i])
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

# ____________________________________________________________

def rewrite_operation(op):
    try:
        return _rewrite_ops[op.opname](op)
    except KeyError:
        return op

def rewrite_op_direct_call(op):
    """Turn direct_call(fn, i1, i2, ref1, ref2)
       into residual_call_ir(fn, [i1, i2], [ref1, ref2])
       (or residual_call_r or residual_call_irf)."""
    args_i = []
    args_r = []
    args_f = []
    for v in op.args[1:]:
        add_in_correct_list(v, args_i, args_r, args_f)
    if args_f:   kinds = 'irf'
    elif args_i: kinds = 'ir'
    else:        kinds = 'r'
    sublists = []
    if 'i' in kinds: sublists.append(args_i)
    if 'r' in kinds: sublists.append(args_r)
    if 'f' in kinds: sublists.append(args_f)
    return SpaceOperation('residual_call_' + kinds,
                          [op.args[0]] + sublists,
                          op.result)

def add_in_correct_list(v, lst_i, lst_r, lst_f):
    kind = getkind(v.concretetype)
    if kind == 'void': return
    elif kind == 'int': lst = lst_i
    elif kind == 'ref': lst = lst_r
    elif kind == 'float': lst = lst_f
    else: raise AssertionError(kind)
    lst.append(v)

# ____________________________________________________________

_rewrite_ops = {}
for _name, _func in globals().items():
    if _name.startswith('rewrite_op_'):
        _rewrite_ops[_name[len('rewrite_op_'):]] = _func
