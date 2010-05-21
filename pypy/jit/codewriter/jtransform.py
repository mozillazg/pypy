import py, sys
from pypy.rpython.lltypesystem import lltype, rstr
from pypy.rpython import rlist
from pypy.jit.metainterp.history import getkind
from pypy.objspace.flow.model import SpaceOperation, Variable, Constant
from pypy.objspace.flow.model import Block, Link, c_last_exception
from pypy.jit.codewriter.flatten import ListOfKind, IndirectCallTargets
from pypy.jit.codewriter import support, heaptracker
from pypy.jit.metainterp.typesystem import deref, arrayItem
from pypy.rlib import objectmodel
from pypy.rlib.jit import _we_are_jitted
from pypy.translator.simplify import get_funcobj


def transform_graph(graph, cpu=None, callcontrol=None, portal=True):
    """Transform a control flow graph to make it suitable for
    being flattened in a JitCode.
    """
    t = Transformer(cpu, callcontrol)
    t.transform(graph, portal)


class Transformer(object):

    def __init__(self, cpu=None, callcontrol=None):
        self.cpu = cpu
        self.callcontrol = callcontrol

    def transform(self, graph, portal):
        self.graph = graph
        self.portal = portal
        for block in list(graph.iterblocks()):
            self.optimize_block(block)

    def optimize_block(self, block):
        if block.operations == ():
            return
        renamings = {}
        renamings_constants = {}    # subset of 'renamings', {Var:Const} only
        newoperations = []
        #
        def do_rename(var, var_or_const):
            renamings[var] = var_or_const
            if isinstance(var_or_const, Constant):
                renamings_constants[var] = var_or_const
        #
        for op in block.operations:
            if renamings_constants:
                op = self._do_renaming(renamings_constants, op)
            oplist = self.rewrite_operation(op)
            #
            count_before_last_operation = len(newoperations)
            if not isinstance(oplist, list):
                oplist = [oplist]
            for op1 in oplist:
                if isinstance(op1, SpaceOperation):
                    newoperations.append(self._do_renaming(renamings, op1))
                elif op1 is None:
                    # rewrite_operation() returns None to mean "has no real
                    # effect, the result should just be renamed to args[0]"
                    if op.result is not None:
                        do_rename(op.result, renamings.get(op.args[0],
                                                           op.args[0]))
                elif isinstance(op1, Constant):
                    do_rename(op.result, op1)
                else:
                    raise TypeError(repr(op1))
        #
        if block.exitswitch == c_last_exception:
            if len(newoperations) == count_before_last_operation:
                self._killed_exception_raising_operation(block)
        block.operations = newoperations
        block.exitswitch = renamings.get(block.exitswitch, block.exitswitch)
        self.follow_constant_exit(block)
        self.optimize_goto_if_not(block)
        for link in block.exits:
            self._do_renaming_on_link(renamings, link)

    def _do_renaming(self, rename, op):
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

    def _do_renaming_on_link(self, rename, link):
        for i, v in enumerate(link.args):
            if isinstance(v, Variable):
                if v in rename:
                    link.args[i] = rename[v]

    def _killed_exception_raising_operation(self, block):
        assert block.exits[0].exitcase is None
        del block.exits[1:]
        block.exitswitch = None

    # ----------

    def follow_constant_exit(self, block):
        v = block.exitswitch
        if isinstance(v, Constant) and v != c_last_exception:
            llvalue = v.value
            for link in block.exits:
                if link.llexitcase == llvalue:
                    break
            else:
                assert link.exitcase == 'default'
            block.exitswitch = None
            link.exitcase = link.llexitcase = None
            block.recloseblock(link)

    def optimize_goto_if_not(self, block):
        """Replace code like 'v = int_gt(x,y); exitswitch = v'
           with just 'exitswitch = ('int_gt',x,y)'."""
        if len(block.exits) != 2:
            return False
        v = block.exitswitch
        if (v == c_last_exception or isinstance(v, tuple)
            or v.concretetype != lltype.Bool):
            return False
        for op in block.operations[::-1]:
            if v in op.args:
                return False   # variable is also used in cur block
            if v is op.result:
                if op.opname not in ('int_lt', 'int_le', 'int_eq', 'int_ne',
                                     'int_gt', 'int_ge',
                                     'int_is_zero', 'int_is_true',
                                     'ptr_eq', 'ptr_ne',
                                     'ptr_iszero', 'ptr_nonzero'):
                    return False    # not a supported operation
                # ok! optimize this case
                block.operations.remove(op)
                block.exitswitch = (op.opname,) + tuple(op.args)
                if op.opname in ('ptr_iszero', 'ptr_nonzero'):
                    block.exitswitch += ('-live-before',)
                # if the variable escape to the next block along a link,
                # replace it with a constant, because we know its value
                for link in block.exits:
                    while v in link.args:
                        index = link.args.index(v)
                        link.args[index] = Constant(link.llexitcase,
                                                    lltype.Bool)
                return True
        return False

    # ----------

    def rewrite_operation(self, op):
        try:
            rewrite = _rewrite_ops[op.opname]
        except KeyError:
            return op     # default: keep the operation unchanged
        else:
            return rewrite(self, op)

    def rewrite_op_same_as(self, op): pass
    def rewrite_op_cast_pointer(self, op): pass
    def rewrite_op_cast_primitive(self, op): pass
    def rewrite_op_cast_bool_to_int(self, op): pass
    def rewrite_op_cast_bool_to_uint(self, op): pass
    def rewrite_op_cast_char_to_int(self, op): pass
    def rewrite_op_cast_unichar_to_int(self, op): pass
    def rewrite_op_cast_int_to_char(self, op): pass
    def rewrite_op_cast_int_to_unichar(self, op): pass
    def rewrite_op_cast_int_to_uint(self, op): pass
    def rewrite_op_cast_uint_to_int(self, op): pass

    def _rewrite_symmetric(self, op):
        """Rewrite 'c1+v2' into 'v2+c1' in an attempt to avoid generating
        too many variants of the bytecode."""
        if (isinstance(op.args[0], Constant) and
            isinstance(op.args[1], Variable)):
            reversename = {'int_lt': 'int_gt',
                           'int_le': 'int_ge',
                           'int_gt': 'int_lt',
                           'int_ge': 'int_le',
                           'float_lt': 'float_gt',
                           'float_le': 'float_ge',
                           'float_gt': 'float_lt',
                           'float_ge': 'float_le',
                           }.get(op.opname, op.opname)
            return SpaceOperation(reversename,
                                  [op.args[1], op.args[0]] + op.args[2:],
                                  op.result)
        else:
            return op

    rewrite_op_int_add = _rewrite_symmetric
    rewrite_op_int_mul = _rewrite_symmetric
    rewrite_op_int_and = _rewrite_symmetric
    rewrite_op_int_or  = _rewrite_symmetric
    rewrite_op_int_xor = _rewrite_symmetric
    rewrite_op_int_lt  = _rewrite_symmetric
    rewrite_op_int_le  = _rewrite_symmetric
    rewrite_op_int_gt  = _rewrite_symmetric
    rewrite_op_int_ge  = _rewrite_symmetric

    rewrite_op_float_add = _rewrite_symmetric
    rewrite_op_float_mul = _rewrite_symmetric
    rewrite_op_float_lt  = _rewrite_symmetric
    rewrite_op_float_le  = _rewrite_symmetric
    rewrite_op_float_gt  = _rewrite_symmetric
    rewrite_op_float_ge  = _rewrite_symmetric

    def rewrite_op_int_add_ovf(self, op):
        op0 = self._rewrite_symmetric(op)
        op1 = SpaceOperation('-live-', [], None)
        return [op0, op1]

    rewrite_op_int_mul_ovf = rewrite_op_int_add_ovf

    def rewrite_op_int_sub_ovf(self, op):
        op1 = SpaceOperation('-live-', [], None)
        return [op, op1]

    # ----------
    # Various kinds of calls

    def rewrite_op_direct_call(self, op):
        kind = self.callcontrol.guess_call_kind(op)
        return getattr(self, 'handle_%s_call' % kind)(op)

    def rewrite_op_indirect_call(self, op):
        kind = self.callcontrol.guess_call_kind(op)
        return getattr(self, 'handle_%s_indirect_call' % kind)(op)

    def rewrite_call(self, op, namebase, initialargs):
        """Turn 'i0 = direct_call(fn, i1, i2, ref1, ref2)'
           into 'i0 = xxx_call_ir_i(fn, descr, [i1,i2], [ref1,ref2])'.
           The name is one of '{residual,direct}_call_{r,ir,irf}_{i,r,f,v}'."""
        lst_i, lst_r, lst_f = self.make_three_lists(op.args[1:])
        reskind = getkind(op.result.concretetype)[0]
        if lst_f or reskind == 'f': kinds = 'irf'
        elif lst_i: kinds = 'ir'
        else: kinds = 'r'
        sublists = []
        if 'i' in kinds: sublists.append(lst_i)
        if 'r' in kinds: sublists.append(lst_r)
        if 'f' in kinds: sublists.append(lst_f)
        return SpaceOperation('%s_%s_%s' % (namebase, kinds, reskind),
                              initialargs + sublists, op.result)

    def make_three_lists(self, vars):
        args_i = []
        args_r = []
        args_f = []
        for v in vars:
            self.add_in_correct_list(v, args_i, args_r, args_f)
        return [ListOfKind('int', args_i),
                ListOfKind('ref', args_r),
                ListOfKind('float', args_f)]

    def add_in_correct_list(self, v, lst_i, lst_r, lst_f):
        kind = getkind(v.concretetype)
        if kind == 'void': return
        elif kind == 'int': lst = lst_i
        elif kind == 'ref': lst = lst_r
        elif kind == 'float': lst = lst_f
        else: raise AssertionError(kind)
        lst.append(v)

    def handle_residual_call(self, op, extraargs=[]):
        """A direct_call turns into the operation 'residual_call_xxx' if it
        is calling a function that we don't want to JIT.  The initial args
        of 'residual_call_xxx' are the function to call, and its calldescr."""
        calldescr = self.callcontrol.getcalldescr(op)
        op1 = self.rewrite_call(op, 'residual_call',
                                [op.args[0], calldescr] + extraargs)
        if self.callcontrol.calldescr_canraise(calldescr):
            op1 = [op1, SpaceOperation('-live-', [], None)]
        return op1

    def handle_regular_call(self, op):
        """A direct_call turns into the operation 'inline_call_xxx' if it
        is calling a function that we want to JIT.  The initial arg of
        'inline_call_xxx' is the JitCode of the called function."""
        [targetgraph] = self.callcontrol.graphs_from(op)
        jitcode = self.callcontrol.get_jitcode(targetgraph,
                                               called_from=self.graph)
        op0 = self.rewrite_call(op, 'inline_call', [jitcode])
        op1 = SpaceOperation('-live-', [], None)
        return [op0, op1]

    def handle_builtin_call(self, op):
        oopspec_name, args = support.decode_builtin_call(op)
        # dispatch to various implementations depending on the oopspec_name
        if oopspec_name.startswith('list.') or oopspec_name == 'newlist':
            prepare = self._handle_list_call
        elif oopspec_name.startswith('virtual_ref'):
            prepare = self._handle_virtual_ref_call
        else:
            prepare = self.prepare_builtin_call
        op1 = prepare(op, oopspec_name, args)
        # If the resulting op1 is still a direct_call, turn it into a
        # residual_call.
        if op1 is None or op1.opname == 'direct_call':
            op1 = self.handle_residual_call(op1 or op)
        return op1

    handle_residual_indirect_call = handle_residual_call

    def handle_regular_indirect_call(self, op):
        """An indirect call where at least one target has a JitCode."""
        lst = []
        for targetgraph in self.callcontrol.graphs_from(op):
            jitcode = self.callcontrol.get_jitcode(targetgraph,
                                                   called_from=self.graph)
            lst.append(jitcode)
        op0 = SpaceOperation('-live-', [], None)
        op1 = SpaceOperation('int_guard_value', [op.args[0]], None)
        op2 = self.handle_residual_call(op, [IndirectCallTargets(lst)])
        result = [op0, op1]
        if isinstance(op2, list):
            result += op2
        else:
            result.append(op2)
        return result

    def prepare_builtin_call(self, op, oopspec_name, args,
                              extra=None, extrakey=None):
        argtypes = [v.concretetype for v in args]
        resulttype = op.result.concretetype
        c_func, TP = support.builtin_func_for_spec(self.cpu.rtyper,
                                                   oopspec_name, argtypes,
                                                   resulttype, extra, extrakey)
        return SpaceOperation('direct_call', [c_func] + args, op.result)

    def _do_builtin_call(self, op, oopspec_name=None, args=None,
                         extra=None, extrakey=None):
        if oopspec_name is None: oopspec_name = op.opname
        if args is None: args = op.args
        op1 = self.prepare_builtin_call(op, oopspec_name, args,
                                        extra, extrakey)
        return self.rewrite_op_direct_call(op1)

    # XXX some of the following functions should not become residual calls
    # but be really compiled
    rewrite_op_int_floordiv_ovf_zer = _do_builtin_call
    rewrite_op_int_floordiv_ovf     = _do_builtin_call
    rewrite_op_int_floordiv_zer     = _do_builtin_call
    rewrite_op_int_mod_ovf_zer = _do_builtin_call
    rewrite_op_int_mod_ovf     = _do_builtin_call
    rewrite_op_int_mod_zer     = _do_builtin_call
    rewrite_op_int_lshift_ovf  = _do_builtin_call
    rewrite_op_int_abs         = _do_builtin_call
    rewrite_op_gc_identityhash = _do_builtin_call

    # ----------
    # getfield/setfield/mallocs etc.

    def rewrite_op_hint(self, op):
        hints = op.args[1].value
        if hints.get('promote') and op.args[0].concretetype is not lltype.Void:
            assert op.args[0].concretetype != lltype.Ptr(rstr.STR)
            kind = getkind(op.args[0].concretetype)
            op0 = SpaceOperation('-live-', [], None)
            op1 = SpaceOperation('%s_guard_value' % kind, [op.args[0]], None)
            # the special return value None forces op.result to be considered
            # equal to op.args[0]
            return [op0, op1, None]
        else:
            log.WARNING('ignoring hint %r at %r' % (hints, self.graph))

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
        if self.is_typeptr_getset(op):
            return self.handle_getfield_typeptr(op)
        # turn the flow graph 'getfield' operation into our own version
        [v_inst, c_fieldname] = op.args
        RESULT = op.result.concretetype
        if RESULT is lltype.Void:
            return
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
        kind = getkind(RESULT)[0]
        return SpaceOperation('getfield_%s_%s%s' % (argname, kind, pure),
                              [v_inst, descr], op.result)

    def rewrite_op_setfield(self, op):
        if self.is_typeptr_getset(op):
            # ignore the operation completely -- instead, it's done by 'new'
            return
        # turn the flow graph 'setfield' operation into our own version
        [v_inst, c_fieldname, v_value] = op.args
        RESULT = v_value.concretetype
        if RESULT is lltype.Void:
            return
        # check for virtualizable
        #if self.is_virtualizable_getset(op):
        #    vinfo = self.codewriter.metainterp_sd.virtualizable_info
        #    index = vinfo.static_field_to_extra_box[op.args[1].value]
        #    self.emit('setfield_vable',
        #              self.var_position(v_inst),
        #              index,
        #              self.var_position(v_value))
        #    return
        argname = getattr(v_inst.concretetype.TO, '_gckind', 'gc')
        descr = self.cpu.fielddescrof(v_inst.concretetype.TO,
                                      c_fieldname.value)
        kind = getkind(RESULT)[0]
        return SpaceOperation('setfield_%s_%s' % (argname, kind),
                              [v_inst, descr, v_value],
                              None)

    def is_typeptr_getset(self, op):
        return (op.args[1].value == 'typeptr' and
                op.args[0].concretetype.TO._hints.get('typeptr'))

    def handle_getfield_typeptr(self, op):
        op0 = SpaceOperation('-live-', [], None)
        op1 = SpaceOperation('guard_class', [op.args[0]], op.result)
        return [op0, op1]

    def rewrite_op_malloc(self, op):
        assert op.args[1].value == {'flavor': 'gc'}
        STRUCT = op.args[0].value
        vtable = heaptracker.get_vtable_for_gcstruct(self.cpu, STRUCT)
        if vtable:
            # do we have a __del__?
            try:
                rtti = lltype.getRuntimeTypeInfo(STRUCT)
            except ValueError:
                pass
            else:
                if hasattr(rtti._obj, 'destructor_funcptr'):
                    RESULT = lltype.Ptr(STRUCT)
                    assert RESULT == op.result.concretetype
                    return self._do_builtin_call(op, 'alloc_with_del', [],
                                                 extra = (RESULT, vtable),
                                                 extrakey = STRUCT)
            heaptracker.register_known_gctype(self.cpu, vtable, STRUCT)
            opname = 'new_with_vtable'
        else:
            opname = 'new'
        sizedescr = self.cpu.sizeof(STRUCT)
        return SpaceOperation(opname, [sizedescr], op.result)

    def rewrite_op_getinteriorarraysize(self, op):
        # only supports strings and unicodes
        assert len(op.args) == 2
        assert op.args[1].value == 'chars'
        optype = op.args[0].concretetype
        if optype == lltype.Ptr(rstr.STR):
            opname = "strlen"
        else:
            assert optype == lltype.Ptr(rstr.UNICODE)
            opname = "unicodelen"
        return SpaceOperation(opname, [op.args[0]], op.result)

    def rewrite_op_getinteriorfield(self, op):
        # only supports strings and unicodes
        assert len(op.args) == 3
        assert op.args[1].value == 'chars'
        optype = op.args[0].concretetype
        if optype == lltype.Ptr(rstr.STR):
            opname = "strgetitem"
        else:
            assert optype == lltype.Ptr(rstr.UNICODE)
            opname = "unicodegetitem"
        return SpaceOperation(opname, [op.args[0], op.args[2]], op.result)

    def rewrite_op_setinteriorfield(self, op):
        # only supports strings and unicodes
        assert len(op.args) == 4
        assert op.args[1].value == 'chars'
        optype = op.args[0].concretetype
        if optype == lltype.Ptr(rstr.STR):
            opname = "strsetitem"
        else:
            assert optype == lltype.Ptr(rstr.UNICODE)
            opname = "unicodesetitem"
        return SpaceOperation(opname, [op.args[0], op.args[2], op.args[3]],
                              op.result)

    def _rewrite_equality(self, op, opname):
        arg0, arg1 = op.args
        if isinstance(arg0, Constant) and not arg0.value:
            return SpaceOperation(opname, [arg1], op.result)
        elif isinstance(arg1, Constant) and not arg1.value:
            return SpaceOperation(opname, [arg0], op.result)
        else:
            return self._rewrite_symmetric(op)

    def _is_gc(self, v):
        return v.concretetype.TO._gckind == 'gc'

    def _rewrite_nongc_ptrs(self, op):
        if self._is_gc(op.args[0]):
            return op
        else:
            opname = {'ptr_eq': 'int_eq',
                      'ptr_ne': 'int_ne',
                      'ptr_iszero': 'int_is_zero',
                      'ptr_nonzero': 'int_is_true'}[op.opname]
            return SpaceOperation(opname, op.args, op.result)

    def rewrite_op_int_eq(self, op):
        return self._rewrite_equality(op, 'int_is_zero')

    def rewrite_op_int_ne(self, op):
        return self._rewrite_equality(op, 'int_is_true')

    def rewrite_op_ptr_eq(self, op):
        op1 = self._rewrite_equality(op, 'ptr_iszero')
        return self._rewrite_nongc_ptrs(op1)

    def rewrite_op_ptr_ne(self, op):
        op1 = self._rewrite_equality(op, 'ptr_nonzero')
        return self._rewrite_nongc_ptrs(op1)

    rewrite_op_ptr_iszero = _rewrite_nongc_ptrs
    rewrite_op_ptr_nonzero = _rewrite_nongc_ptrs

    def rewrite_op_cast_ptr_to_int(self, op):
        if self._is_gc(op.args[0]):
            return op

    # ----------
    # Renames, from the _old opname to the _new one.
    # The new operation is optionally further processed by rewrite_operation().
    for _old, _new in [('bool_not', 'int_is_zero'),
                       ('cast_bool_to_float', 'cast_int_to_float'),
                       ('cast_uint_to_float', 'cast_int_to_float'),
                       ('cast_float_to_uint', 'cast_float_to_int'),

                       ('int_add_nonneg_ovf', 'int_add_ovf'),
                       ('keepalive', '-live-'),

                       ('char_lt', 'int_lt'),
                       ('char_le', 'int_le'),
                       ('char_eq', 'int_eq'),
                       ('char_ne', 'int_ne'),
                       ('char_gt', 'int_gt'),
                       ('char_ge', 'int_ge'),
                       ('unichar_eq', 'int_eq'),
                       ('unichar_ne', 'int_ne'),

                       ('uint_is_true', 'int_is_true'),
                       ('uint_invert', 'int_invert'),
                       ('uint_add', 'int_add'),
                       ('uint_sub', 'int_sub'),
                       ('uint_mul', 'int_mul'),
                       ('uint_floordiv', 'int_floordiv'),
                       ('uint_floordiv_zer', 'int_floordiv_zer'),
                       ('uint_mod', 'int_mod'),
                       ('uint_mod_zer', 'int_mod_zer'),
                       ('uint_lt', 'int_lt'),
                       ('uint_le', 'int_le'),
                       ('uint_eq', 'int_eq'),
                       ('uint_ne', 'int_ne'),
                       ('uint_gt', 'int_gt'),
                       ('uint_ge', 'int_ge'),
                       ('uint_and', 'int_and'),
                       ('uint_or', 'int_or'),
                       ('uint_lshift', 'int_lshift'),
                       ('uint_rshift', 'int_rshift'),
                       ('uint_xor', 'int_xor'),
                       ]:
        assert _old not in locals()
        exec py.code.Source('''
            def rewrite_op_%s(self, op):
                op1 = SpaceOperation(%r, op.args, op.result)
                return self.rewrite_operation(op1)
        ''' % (_old, _new)).compile()

    def rewrite_op_int_neg_ovf(self, op):
        op1 = SpaceOperation('int_sub_ovf',
                             [Constant(0, lltype.Signed), op.args[0]],
                             op.result)
        return self.rewrite_operation(op1)

    def rewrite_op_float_is_true(self, op):
        op1 = SpaceOperation('float_ne',
                             [op.args[0], Constant(0.0, lltype.Float)],
                             op.result)
        return self.rewrite_operation(op1)

    def rewrite_op_int_is_true(self, op):
        if isinstance(op.args[0], Constant):
            value = op.args[0].value
            if value is objectmodel.malloc_zero_filled:
                value = True
            elif value is _we_are_jitted:
                value = True
            else:
                raise AssertionError("don't know the truth value of %r"
                                     % (value,))
            return Constant(value, lltype.Bool)
        return op

    def rewrite_op_jit_marker(self, op):
        jitdriver = op.args[1].value
        self.callcontrol.found_jitdriver(jitdriver)
        key = op.args[0].value
        return getattr(self, 'handle_jit_marker__%s' % key)(op, jitdriver)

    def handle_jit_marker__jit_merge_point(self, op, jitdriver):
        assert self.portal, "jit_merge_point in non-main graph!"
        ops = []
        num_green_args = len(jitdriver.greens)
        for v in op.args[2:2+num_green_args]:
            if isinstance(v, Variable) and v.concretetype is not lltype.Void:
                kind = getkind(v.concretetype)
                ops.append(SpaceOperation('-live-', [], None))
                ops.append(SpaceOperation('%s_guard_value' % kind,
                                          [v], None))
        args = (self.make_three_lists(op.args[2:2+num_green_args]) +
                self.make_three_lists(op.args[2+num_green_args:]))
        ops.append(SpaceOperation('jit_merge_point', args, None))
        return ops

    def handle_jit_marker__can_enter_jit(self, op, jitdriver):
        return SpaceOperation('can_enter_jit', [], None)

    # ----------
    # Lists.

    def _handle_list_call(self, op, oopspec_name, args):
        if oopspec_name.startswith('new'):
            LIST = deref(op.result.concretetype)
        else:
            LIST = deref(args[0].concretetype)
        resizable = isinstance(LIST, lltype.GcStruct)
        assert resizable == (not isinstance(LIST, lltype.GcArray))
        if resizable:
            prefix = 'do_resizable_'
        else:
            prefix = 'do_fixed_'
            if self._array_of_voids(LIST):
                return None # arrays of voids: not supported
            arraydescr = self.cpu.arraydescrof(LIST)
            descrs = (arraydescr,)
        #
        try:
            meth = getattr(self, prefix + oopspec_name.replace('.', '_'))
        except AttributeError:
            return None
        else:
            return meth(op, args, *descrs)

    def do_fixed_newlist(self, op, args, arraydescr):
        # normalize number of arguments
        if len(args) < 1:
            args.append(Constant(0, lltype.Signed))
        if len(args) > 1:
            v_default = args[1]
            ARRAY = deref(op.result.concretetype)
            if (not isinstance(v_default, Constant) or
                v_default.value != arrayItem(ARRAY)._defl()):
                return None     # variable or non-null initial value
        return SpaceOperation('new_array', [arraydescr, args[0]], op.result)

    def do_fixed_list_len(self, op, args, arraydescr):
        return SpaceOperation('arraylen_gc', [args[0], arraydescr], op.result)

    do_fixed_list_len_foldable = do_fixed_list_len

    def _get_list_nonneg_canraise_flags(self, op):
        # xxx break of abstraction:
        func = get_funcobj(op.args[0].value)._callable
        # base hints on the name of the ll function, which is a bit xxx-ish
        # but which is safe for now
        assert func.func_name.startswith('ll_')
        non_negative = '_nonneg' in func.func_name
        fast = '_fast' in func.func_name
        if fast:
            can_raise = False
            non_negative = True
        else:
            tag = op.args[1].value
            assert tag in (rlist.dum_nocheck, rlist.dum_checkidx)
            can_raise = tag != rlist.dum_nocheck
        return non_negative, can_raise

    def _prepare_list_getset(self, op, descr, args, checkname):
        non_negative, can_raise = self._get_list_nonneg_canraise_flags(op)
        if can_raise:
            return None, None
        if non_negative:
            return args[1], []
        else:
            v_posindex = Variable('posindex')
            v_posindex.concretetype = lltype.Signed
            op = SpaceOperation(checkname, [args[0],
                                            descr, args[1]], v_posindex)
            return v_posindex, [op]

    def do_fixed_list_getitem(self, op, args, arraydescr, pure=False):
        v_index, extraop = self._prepare_list_getset(op, arraydescr, args,
                                                     'check_neg_index')
        if v_index is None:
            return None
        extra = getkind(op.result.concretetype)[0]
        if pure:
            extra = 'pure_' + extra
        op = SpaceOperation('getarrayitem_gc_%s' % extra,
                            [args[0], arraydescr, v_index], op.result)
        return extraop + [op]

    def do_fixed_list_getitem_foldable(self, op, args, arraydescr):
        return self.do_fixed_list_getitem(op, args, arraydescr, pure=True)

    def do_fixed_list_setitem(self, op, args, arraydescr):
        v_index, extraop = self._prepare_list_getset(op, arraydescr, args,
                                                     'check_neg_index')
        if v_index is None:
            return None
        kind = getkind(op.args[2].concretetype)[0]
        op = SpaceOperation('setarrayitem_gc_%s' % kind,
                            [args[0], arraydescr, v_index, args[2]], None)
        return extraop + [op]

    # ----------
    # VirtualRefs.

    def _handle_virtual_ref_call(self, op, oopspec_name, args):
        vrefinfo = self.callcontrol.virtualref_info
        heaptracker.register_known_gctype(self.cpu,
                                          vrefinfo.jit_virtual_ref_vtable,
                                          vrefinfo.JIT_VIRTUAL_REF)
        return SpaceOperation(oopspec_name, list(args), op.result)

    def rewrite_op_jit_force_virtual(self, op):
        return self._do_builtin_call(op)

# ____________________________________________________________

def _with_prefix(prefix):
    result = {}
    for name in dir(Transformer):
        if name.startswith(prefix):
            result[name[len(prefix):]] = getattr(Transformer, name)
    return result

_rewrite_ops = _with_prefix('rewrite_op_')
