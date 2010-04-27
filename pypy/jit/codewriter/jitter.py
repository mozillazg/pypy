import sys
from pypy.rpython.lltypesystem import lltype, rstr
from pypy.jit.metainterp.history import getkind
from pypy.objspace.flow.model import SpaceOperation, Variable, Constant
from pypy.objspace.flow.model import Block, Link, c_last_exception
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
        for block in list(graph.iterblocks()):
            self.optimize_block(block)

    def optimize_block(self, block):
        if block.operations == ():
            return
        rename = {}
        newoperations = []
        if block.exitswitch == c_last_exception:
            op_raising_exception = block.operations[-1]
            self.rewrite_exception_operation(op_raising_exception, block)
        else:
            op_raising_exception = Ellipsis
        for op in block.operations:
            try:
                op1 = self.rewrite_operation(op)
            except NoOp:
                if op.result is not None:
                    rename[op.result] = rename.get(op.args[0], op.args[0])
                if op is op_raising_exception:
                    self.killed_exception_raising_operation(block)
            else:
                op2 = self.do_renaming(rename, op1)
                newoperations.append(op2)
        block.operations = newoperations
        self.optimize_goto_if_not(block)
        for link in block.exits:
            self.do_renaming_on_link(rename, link)

    def do_renaming(self, rename, op):
        op = SpaceOperation(op.opname, op.args[:], op.result)
        for i, v in enumerate(op.args):
            if isinstance(v, Variable):
                if v in rename:
                    op.args[i] = rename[v]
            elif isinstance(v, ListOfKind):
                newlst = []
                for x in v:
                    if x in rename:
                        x = rename[x]
                    newlst.append(x)
                op.args[i] = ListOfKind(v.kind, newlst)
        return op

    def do_renaming_on_link(self, rename, link):
        for i, v in enumerate(link.args):
            if isinstance(v, Variable):
                if v in rename:
                    link.args[i] = rename[v]

    def killed_exception_raising_operation(self, block):
        assert block.exits[0].exitcase is None
        del block.exits[1:]
        block.exitswitch = None

    # ----------

    def optimize_goto_if_not(self, block):
        """Replace code like 'v = int_gt(x,y); exitswitch = v'
           with just 'exitswitch = ('int_gt',x,y)'."""
        if len(block.exits) != 2:
            return False
        v = block.exitswitch
        if isinstance(v, tuple) or v.concretetype != lltype.Bool:
            return False
        for link in block.exits:
            if v in link.args:
                return False   # variable escapes to next block
        for op in block.operations[::-1]:
            if v in op.args:
                return False   # variable is also used in cur block
            if v is op.result:
                if op.opname not in ('int_lt', 'int_le', 'int_eq', 'int_ne',
                                     'int_gt', 'int_ge', 'int_is_true'):
                    return False    # not a supported operation
                # ok! optimize this case
                block.operations.remove(op)
                opname = op.opname
                args = op.args
                if op.opname in ('int_ne', 'int_eq'):
                    if isinstance(args[0], Constant):
                        args = args[::-1]
                    if isinstance(args[1], Constant) and args[1].value == 0:
                        if opname == 'int_eq':
                            # must invert the two exit links
                            link = block.exits[0]
                            link.llexitcase = link.exitcase = not link.exitcase
                            link = block.exits[1]
                            link.llexitcase = link.exitcase = not link.exitcase
                        opname = 'int_is_true'
                        args = [args[0]]
                block.exitswitch = (opname,) + tuple(args)
                return True
        return False

    # ----------

    def rewrite_exception_operation(self, op, block):
        # mangling of the graph for exception-raising operations that are
        # not simple calls
        try:
            rewrite = _rewrite_exc_ops[op.opname]
        except KeyError:
            pass
        else:
            rewrite(self, op, block)

    def rewrite_exc_op_int_floordiv_ovf_zer(self, op, block):
        # See test_flatten.test_int_floordiv_ovf_zer for the mangling done here
        usedvars = self.list_vars_in_use_at_end(block, op.args, op.result)
        block.operations.pop()
        [ovf_link, zer_link] = self.extract_exc_links(block, [
            OverflowError, ZeroDivisionError])
        block = self.write_new_condition(block, usedvars, zer_link,
                                         ('int_is_true', op.args[1]))
        v1 = Variable(); v1.concretetype = lltype.Signed
        v2 = Variable(); v2.concretetype = lltype.Signed
        block.operations += [
            SpaceOperation('int_add', [op.args[0],
                                       Constant(sys.maxint, lltype.Signed)],
                           v1),
            SpaceOperation('int_and', [v1, op.args[1]], v2),
            ]
        block = self.write_new_condition(block, usedvars, ovf_link,
                                 ('int_ne', v2, Constant(-1, lltype.Signed)))
        block.operations += [
            SpaceOperation('int_floordiv', op.args, op.result),
            ]

    def list_vars_in_use_at_end(self, block, extravars=[], exclude=None):
        lists = [extravars]
        for link in block.exits:
            lists.append(link.args)
        in_use = set()
        for lst in lists:
            for v in lst:
                if isinstance(v, Variable):
                    in_use.add(v)
        if exclude in in_use:
            in_use.remove(exclude)
        return list(in_use)

    def extract_exc_links(self, block, exceptions):
        # Remove the exception links from the block.  The exception links must
        # be catching exactly the listed 'exceptions'.  We return them to the
        # caller.
        assert block.exits[0].exitcase is None
        real_exc_links = dict([(link.exitcase, link)
                               for link in block.exits[1:]])
        assert dict.fromkeys(real_exc_links) == dict.fromkeys(exceptions)
        block.recloseblock(block.exits[0])
        return [real_exc_links[exc] for exc in exceptions]

    def write_new_condition(self, block, usedvars, exc_link, exitswitch):
        # Write an exit at the end of the block, going either to a new
        # block that is the continuation of the current block, or (in case
        # 'exitswitch' is False) following the given 'exc_link'.
        newblock = Block(usedvars)
        normal_link = Link(usedvars, newblock)
        normal_link.exitcase = normal_link.llexitcase = True
        exc_link.exitcase    = exc_link.llexitcase    = False
        block.exitswitch = exitswitch
        [exit] = block.exits
        block.recloseblock(normal_link, exc_link)
        newblock.closeblock(exit)
        return newblock

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
    def rewrite_op_cast_pointer(self, op): raise NoOp

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
            assert op.args[0].concretetype != lltype.Ptr(rstr.STR)
            kind = getkind(op.args[0].concretetype)
            return SpaceOperation('%s_guard_value' % kind,
                                  [op.args[0]], op.result)
        else:
            log.WARNING('ignoring hint %r at %r' % (hints, self.graph))
            raise NoOp

    def rewrite_op_malloc_varsize(self, op):
        assert op.args[1].value == {'flavor': 'gc'}
        if op.args[0].value == rstr.STR:
            return SpaceOperation('newstr', [op.args[2]], op.result)
        elif op.args[0].value == rstr.UNICODE:
            return SpaceOperation('newunicode', [op.args[2]], op.result)
        else:
            # XXX only strings or simple arrays for now
            ARRAY = op.args[0].value
            arraydescr = self.cpu.arraydescrof(ARRAY)
            return SpaceOperation('new_array', [arraydescr, op.args[2]],
                                  op.result)

    def rewrite_op_setarrayitem(self, op):
        ARRAY = op.args[0].concretetype.TO
        assert ARRAY._gckind == 'gc'
        if self._array_of_voids(ARRAY):
            return
##        if op.args[0] in self.vable_array_vars:     # for virtualizables
##            (v_base, arrayindex) = self.vable_array_vars[op.args[0]]
##            self.emit('setarrayitem_vable',
##                      self.var_position(v_base),
##                      arrayindex,
##                      self.var_position(op.args[1]),
##                      self.var_position(op.args[2]))
##            return
        arraydescr = self.cpu.arraydescrof(ARRAY)
        kind = getkind(op.args[2].concretetype)
        return SpaceOperation('setarrayitem_gc_%s' % kind[0],
                              [arraydescr] + op.args, None)

    def _array_of_voids(self, ARRAY):
        #if isinstance(ARRAY, ootype.Array):
        #    return ARRAY.ITEM == ootype.Void
        #else:
        return ARRAY.OF == lltype.Void

    def rewrite_op_getfield(self, op):
        #if self.is_typeptr_getset(op):
        #    self.handle_getfield_typeptr(op)
        #    return
        # turn the flow graph 'getfield' operation into our own version
        [v_inst, c_fieldname] = op.args
        RESULT = op.result.concretetype
        if RESULT is lltype.Void:
            raise NoOp
        # check for virtualizable
        #try:
        #    if self.is_virtualizable_getset(op):
        #        vinfo = self.codewriter.metainterp_sd.virtualizable_info
        #        index = vinfo.static_field_to_extra_box[op.args[1].value]
        #        self.emit('getfield_vable',
        #                  self.var_position(v_inst),
        #                  index)
        #        self.register_var(op.result)
        #        return
        #except VirtualizableArrayField:
        #    # xxx hack hack hack
        #    vinfo = self.codewriter.metainterp_sd.virtualizable_info
        #    arrayindex = vinfo.array_field_counter[op.args[1].value]
        #    self.vable_array_vars[op.result] = (op.args[0], arrayindex)
        #    return
        # check for deepfrozen structures that force constant-folding
        hints = v_inst.concretetype.TO._hints
        accessor = hints.get("immutable_fields")
        if accessor and c_fieldname.value in accessor.fields:
            pure = '_pure'
            if accessor.fields[c_fieldname.value] == "[*]":
                self.immutable_arrays[op.result] = True
        elif hints.get('immutable'):
            pure = '_pure'
        else:
            pure = ''
        argname = getattr(v_inst.concretetype.TO, '_gckind', 'gc')
        descr = self.cpu.fielddescrof(v_inst.concretetype.TO,
                                      c_fieldname.value)
        if isinstance(RESULT, lltype.Primitive):
            kind = primitive_type_size[RESULT]
        else:
            kind = getkind(RESULT)[0]
        return SpaceOperation('getfield_%s_%s%s' % (argname, kind, pure),
                              [v_inst, descr], op.result)

# ____________________________________________________________

def _with_prefix(prefix):
    result = {}
    for name in dir(Transformer):
        if name.startswith(prefix):
            result[name[len(prefix):]] = getattr(Transformer, name)
    return result

_rewrite_ops     = _with_prefix('rewrite_op_')
_rewrite_exc_ops = _with_prefix('rewrite_exc_op_')

primitive_type_size = {
    lltype.Signed:   'i',
    lltype.Unsigned: 'i',
    lltype.Bool:     'c',
    lltype.Char:     'c',
    lltype.UniChar:  'u',
    lltype.Float:    'f',
    }
