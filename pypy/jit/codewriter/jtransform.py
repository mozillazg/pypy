import py, sys
from pypy.rpython.lltypesystem import lltype, rstr
from pypy.jit.metainterp.history import getkind
from pypy.objspace.flow.model import SpaceOperation, Variable, Constant
from pypy.objspace.flow.model import Block, Link, c_last_exception
from pypy.jit.codewriter.flatten import ListOfKind
from pypy.jit.codewriter import support, heaptracker
from pypy.translator.simplify import get_funcobj


def transform_graph(graph, cpu=None, callcontrol=None, portal=True):
    """Transform a control flow graph to make it suitable for
    being flattened in a JitCode.
    """
    t = Transformer(cpu, callcontrol)
    t.transform(graph, portal)


class NoOp(Exception):
    pass


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
        rename = {}
        newoperations = []
        if block.exitswitch == c_last_exception:
            op_raising_exception = block.operations[-1]
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
        if (v == c_last_exception or isinstance(v, tuple)
            or v.concretetype != lltype.Bool):
            return False
        for link in block.exits:
            if v in link.args:
                return False   # variable escapes to next block
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
    def rewrite_op_cast_pointer(self, op): raise NoOp
    def rewrite_op_cast_primitive(self, op): raise NoOp
    def rewrite_op_cast_bool_to_int(self, op): raise NoOp
    def rewrite_op_cast_bool_to_uint(self, op): raise NoOp
    def rewrite_op_cast_char_to_int(self, op): raise NoOp
    def rewrite_op_cast_unichar_to_int(self, op): raise NoOp
    def rewrite_op_cast_int_to_char(self, op): raise NoOp
    def rewrite_op_cast_int_to_unichar(self, op): raise NoOp
    def rewrite_op_cast_int_to_uint(self, op): raise NoOp
    def rewrite_op_cast_uint_to_int(self, op): raise NoOp

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

    rewrite_op_G_int_add_ovf = _rewrite_symmetric
    rewrite_op_G_int_mul_ovf = _rewrite_symmetric

    rewrite_op_float_add = _rewrite_symmetric
    rewrite_op_float_mul = _rewrite_symmetric
    rewrite_op_float_lt  = _rewrite_symmetric
    rewrite_op_float_le  = _rewrite_symmetric
    rewrite_op_float_gt  = _rewrite_symmetric
    rewrite_op_float_ge  = _rewrite_symmetric

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
        return SpaceOperation('%s_%s_%s' % (namebase, kinds, reskind),
                              initialargs + sublists, op.result)

    def add_in_correct_list(self, v, lst_i, lst_r, lst_f):
        kind = getkind(v.concretetype)
        if kind == 'void': return
        elif kind == 'int': lst = lst_i
        elif kind == 'ref': lst = lst_r
        elif kind == 'float': lst = lst_f
        else: raise AssertionError(kind)
        lst.append(v)

    def handle_residual_call(self, op):
        """A direct_call turns into the operation 'residual_call_xxx' if it
        is calling a function that we don't want to JIT.  The initial args
        of 'residual_call_xxx' are the constant function to call, and its
        calldescr."""
        calldescr, canraise = self.callcontrol.getcalldescr(op)
        #
        pure = False
        loopinvariant = False
        if op.opname == "direct_call":
            func = getattr(get_funcobj(op.args[0].value), '_callable', None)
            pure = getattr(func, "_pure_function_", False)
            loopinvariant = getattr(func, "_jit_loop_invariant_", False)
            if pure or loopinvariant:
                effectinfo = calldescr.get_extra_info()
                assert (effectinfo is not None and
                        not effectinfo.forces_virtual_or_virtualizable)
        if loopinvariant:
            name = 'G_residual_call_loopinvariant'
            assert not non_void_args, ("arguments not supported for "
                                       "loop-invariant function!")
        elif pure:
            # XXX check what to do about exceptions (also MemoryError?)
            name = 'residual_call_pure'
        elif canraise:
            name = 'G_residual_call'
        else:
            name = 'residual_call'
        return self.rewrite_call(op, name, [op.args[0], calldescr])

    def handle_regular_call(self, op):
        """A direct_call turns into the operation 'inline_call_xxx' if it
        is calling a function that we want to JIT.  The initial arg of
        'inline_call_xxx' is the JitCode of the called function."""
        [targetgraph] = self.callcontrol.graphs_from(op)
        jitcode = self.callcontrol.get_jitcode(targetgraph,
                                               called_from=self.graph)
        return self.rewrite_call(op, 'G_inline_call', [jitcode])

    def _do_builtin_call(self, op, oopspec_name=None, args=None, extra=None):
        if oopspec_name is None: oopspec_name = op.opname
        if args is None: args = op.args
        argtypes = [v.concretetype for v in args]
        resulttype = op.result.concretetype
        c_func, TP = support.builtin_func_for_spec(self.cpu.rtyper,
                                                   oopspec_name, argtypes,
                                                   resulttype, extra)
        op1 = SpaceOperation('direct_call', [c_func] + args, op.result)
        return self.rewrite_op_direct_call(op1)

    rewrite_op_int_floordiv_ovf_zer = _do_builtin_call
    rewrite_op_int_floordiv_ovf     = _do_builtin_call
    rewrite_op_int_floordiv_zer     = _do_builtin_call
    rewrite_op_int_mod_ovf_zer = _do_builtin_call
    rewrite_op_int_mod_ovf     = _do_builtin_call
    rewrite_op_int_mod_zer     = _do_builtin_call
    rewrite_op_int_lshift_ovf  = _do_builtin_call
    rewrite_op_gc_identityhash = _do_builtin_call

    # ----------
    # getfield/setfield/mallocs etc.

    def rewrite_op_hint(self, op):
        hints = op.args[1].value
        if hints.get('promote') and op.args[0].concretetype is not lltype.Void:
            assert op.args[0].concretetype != lltype.Ptr(rstr.STR)
            kind = getkind(op.args[0].concretetype)
            # note: the 'G_' prefix tells that the operation might generate
            # a guard in pyjitpl (see liveness.py)
            return SpaceOperation('G_%s_guard_value' % kind,
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
        if self.is_typeptr_getset(op):
            return self.handle_getfield_typeptr(op)
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
        kind = getkind(RESULT)[0]
        return SpaceOperation('getfield_%s_%s%s' % (argname, kind, pure),
                              [v_inst, descr], op.result)

    def rewrite_op_setfield(self, op):
        if self.is_typeptr_getset(op):
            # ignore the operation completely -- instead, it's done by 'new'
            raise NoOp
        # turn the flow graph 'setfield' operation into our own version
        [v_inst, c_fieldname, v_value] = op.args
        RESULT = v_value.concretetype
        if RESULT is lltype.Void:
            raise NoOp
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
        # note: the 'G_' prefix tells that the operation might generate
        # a guard in pyjitpl (see liveness.py)
        return SpaceOperation('G_guard_class', [op.args[0]], op.result)

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
                    return self._do_builtin_call(op, 'alloc_with_del',
                                                 [], extra = (RESULT, vtable))
            # store the vtable as an address -- that's fine, because the
            # GC doesn't need to follow them
            #self.codewriter.register_known_gctype(vtable, STRUCT)
            sizevtabledescr = self.cpu.sizevtableof(STRUCT, vtable)
            return SpaceOperation('new_with_vtable', [sizevtabledescr],
                                  op.result)
        else:
            sizedescr = self.cpu.sizeof(STRUCT)
            return SpaceOperation('new', [sizedescr], op.result)

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
        else:
            raise NoOp

    # ----------
    # Renames, from the _old opname to the _new one.
    # The new operation is optionally further processed by rewrite_operation().
    for _old, _new in [('bool_not', 'int_is_zero'),
                       ('cast_bool_to_float', 'cast_int_to_float'),
                       ('cast_uint_to_float', 'cast_int_to_float'),
                       ('cast_float_to_uint', 'cast_float_to_int'),

                       ('int_add_ovf',        'G_int_add_ovf'),
                       ('int_add_nonneg_ovf', 'G_int_add_ovf'),
                       ('int_sub_ovf',        'G_int_sub_ovf'),
                       ('int_mul_ovf',        'G_int_mul_ovf'),

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

# ____________________________________________________________

def _with_prefix(prefix):
    result = {}
    for name in dir(Transformer):
        if name.startswith(prefix):
            result[name[len(prefix):]] = getattr(Transformer, name)
    return result

_rewrite_ops = _with_prefix('rewrite_op_')
