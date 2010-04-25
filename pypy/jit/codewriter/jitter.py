from pypy.rpython.lltypesystem import lltype
from pypy.jit.metainterp.history import getkind
from pypy.objspace.flow.model import SpaceOperation
from pypy.jit.codewriter.flatten import ListOfKind


def transform_graph(graph, cpu=None):
    """Transform a control flow graph to make it suitable for
    being flattened in a JitCode.
    """
    t = Transformer(cpu)
    t.transform(graph)


class NoOp(Exception):
    pass


class Transformer(object):

    def __init__(self, cpu=None):
        self.cpu = cpu

    def transform(self, graph):
        self.graph = graph
        for block in graph.iterblocks():
            rename = {}
            newoperations = []
            for op in block.operations:
                for i, v in enumerate(op.args):
                    if v in rename:
                        op = SpaceOperation(op.opname, op.args[:],
                                            op.result)
                        op.args[i] = rename[v]
                try:
                    newoperations.append(self.rewrite_operation(op))
                except NoOp:
                    if op.result is not None:
                        rename[op.result] = rename.get(op.args[0], op.args[0])
            block.operations = newoperations
            self.optimize_goto_if_not(block)

    # ----------

    def optimize_goto_if_not(self, block):
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

    # ----------

    def rewrite_operation(self, op):
        try:
            rewrite = _rewrite_ops[op.opname]
        except KeyError:
            return op
        else:
            return rewrite(self, op)

    def rewrite_op_same_as(self, op): raise NoOp
    def rewrite_op_cast_int_to_char(self, op): raise NoOp
    def rewrite_op_cast_int_to_unichar(self, op): raise NoOp
    def rewrite_op_cast_char_to_int(self, op): raise NoOp
    def rewrite_op_cast_unichar_to_int(self, op): raise NoOp

    def rewrite_op_direct_call(self, op):
        """Turn 'i0 = direct_call(fn, i1, i2, ref1, ref2)'
           into e.g. 'i0 = residual_call_ir_i(fn, [i1, i2], [ref1, ref2])'.
           The name is one of 'residual_call_{r,ir,irf}_{i,r,f,v}'."""
        args_i = []
        args_r = []
        args_f = []
        for v in op.args[1:]:
            self.add_in_correct_list(v, args_i, args_r, args_f)
        if args_f:   kinds = 'irf'
        elif args_i: kinds = 'ir'
        else:        kinds = 'r'
        sublists = []
        if 'i' in kinds: sublists.append(ListOfKind('int', args_i))
        if 'r' in kinds: sublists.append(ListOfKind('ref', args_r))
        if 'f' in kinds: sublists.append(ListOfKind('float', args_f))
        reskind = getkind(op.result.concretetype)[0]
        FUNC = op.args[0].concretetype.TO
        NONVOIDARGS = tuple([ARG for ARG in FUNC.ARGS if ARG != lltype.Void])
        calldescr = self.cpu.calldescrof(FUNC, NONVOIDARGS, FUNC.RESULT)
        return SpaceOperation('residual_call_%s_%s' % (kinds, reskind),
                              [op.args[0], calldescr] + sublists,
                              op.result)

    def add_in_correct_list(self, v, lst_i, lst_r, lst_f):
        kind = getkind(v.concretetype)
        if kind == 'void': return
        elif kind == 'int': lst = lst_i
        elif kind == 'ref': lst = lst_r
        elif kind == 'float': lst = lst_f
        else: raise AssertionError(kind)
        lst.append(v)

    def rewrite_op_hint(self, op):
        hints = op.args[1].value
        if hints.get('promote') and op.args[0].concretetype is not lltype.Void:
            #self.minimize_variables()
            from pypy.rpython.lltypesystem.rstr import STR
            assert op.args[0].concretetype != lltype.Ptr(STR)
            kind = getkind(op.args[0].concretetype)
            return SpaceOperation('%s_guard_value' % kind,
                                  [op.args[0]], op.result)
        else:
            log.WARNING('ignoring hint %r at %r' % (hints, self.graph))
            raise NoOp

# ____________________________________________________________

_rewrite_ops = {}
for _name in dir(Transformer):
    if _name.startswith('rewrite_op_'):
        _rewrite_ops[_name[len('rewrite_op_'):]] = getattr(Transformer, _name)
