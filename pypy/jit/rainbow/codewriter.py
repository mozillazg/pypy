from pypy.rlib.unroll import unrolling_iterable
from pypy.rlib.objectmodel import we_are_translated
from pypy.objspace.flow import model as flowmodel
from pypy.rpython.lltypesystem import lltype
from pypy.jit.hintannotator.model import originalconcretetype
from pypy.jit.hintannotator import model as hintmodel
from pypy.jit.timeshifter import rtimeshift, rvalue, rcontainer, exception
from pypy.jit.timeshifter import oop
from pypy.jit.timeshifter.greenkey import KeyDesc
from pypy.jit.rainbow.interpreter import JitCode, JitInterpreter
from pypy.translator.backendopt.removenoops import remove_same_as


class BytecodeWriter(object):
    def __init__(self, t, hannotator, RGenOp):
        self.translator = t
        self.rtyper = hannotator.base_translator.rtyper
        self.hannotator = hannotator
        etrafo = hannotator.exceptiontransformer
        type_system = self.rtyper.type_system.name
        self.exceptiondesc = exception.ExceptionDesc(
            RGenOp, etrafo, type_system, False)
        self.interpreter = JitInterpreter(self.exceptiondesc)
        self.RGenOp = RGenOp
        self.current_block = None
        self.raise_analyzer = hannotator.exceptiontransformer.raise_analyzer
        self.all_graphs = {} # mapping graph to bytecode
        self.unfinished_graphs = []

    def can_raise(self, op):
        return self.raise_analyzer.analyze(op)

    def make_bytecode(self, graph, is_portal=True):
        remove_same_as(graph)
        if is_portal:
            self.all_graphs[graph] = JitCode.__new__(JitCode)
        self.seen_blocks = {}
        self.assembler = []
        self.constants = []
        self.typekinds = []
        self.redboxclasses = []
        self.keydescs = []
        self.structtypedescs = []
        self.fielddescs = []
        self.arrayfielddescs = []
        self.interiordescs = []
        self.oopspecdescs = []
        self.called_bytecodes = []
        self.num_mergepoints = 0
        self.graph_color = self.graph_calling_color(graph)
        self.nonrainbow_functions = []
        self.is_portal = is_portal
        # mapping constant -> index in constants
        self.const_positions = {}
        # mapping blocks to True
        self.seen_blocks = {}
        self.redvar_positions = {}
        # mapping block to the free red index
        self.free_red = {}
        self.greenvar_positions = {}
        # mapping block to the free green index
        self.free_green = {}
        # mapping TYPE to index
        self.type_positions = {}
        # mapping tuples of green TYPES to index
        self.keydesc_positions = {}
        # mapping STRUCTS to index
        self.structtypedesc_positions = {}
        # mapping tuples of STRUCT, name to index
        self.fielddesc_positions = {}
        # mapping ARRAYS to index
        self.arrayfielddesc_positions = {}
        # mapping (TYPE, path) to index
        self.interiordesc_positions = {}
        # mapping (fnobj, can_raise) to index
        self.oopspecdesc_positions = {}
        # mapping graphs to index
        self.graph_positions = {}
        # mapping fnobjs to index
        self.nonrainbow_positions = {}

        self.graph = graph
        self.entrymap = flowmodel.mkentrymap(graph)
        self.make_bytecode_block(graph.startblock)
        assert self.current_block is None
        bytecode = self.all_graphs[graph]
        bytecode.__init__(graph.name,
                          assemble(self.interpreter, *self.assembler),
                          self.constants,
                          self.typekinds,
                          self.redboxclasses,
                          self.keydescs,
                          self.structtypedescs,
                          self.fielddescs,
                          self.arrayfielddescs,
                          self.interiordescs,
                          self.oopspecdescs,
                          self.called_bytecodes,
                          self.num_mergepoints,
                          self.graph_color,
                          self.nonrainbow_functions,
                          self.is_portal)
        if is_portal:
            self.finish_all_graphs()
            return bytecode

    def finish_all_graphs(self):
        while self.unfinished_graphs:
            graph = self.unfinished_graphs.pop()
            self.make_bytecode(graph, is_portal=False)

    def make_bytecode_block(self, block, insert_goto=False):
        if block in self.seen_blocks:
            if insert_goto:
                self.emit("goto")
                self.emit(tlabel(block))
            return
        # inserting a goto not necessary, falling through
        self.seen_blocks[block] = True
        oldblock = self.current_block
        self.free_green[block] = 0
        self.free_red[block] = 0
        self.current_block = block

        self.emit(label(block))
        reds, greens = self.sort_by_color(block.inputargs)
        for arg in reds:
            self.register_redvar(arg)
        for arg in greens:
            self.register_greenvar(arg)
        self.insert_merges(block)
        for op in block.operations:
            self.serialize_op(op)
        self.insert_exits(block)
        self.current_block = oldblock

    def insert_exits(self, block):
        if block.exits == ():
            returnvar, = block.inputargs
            color = self.graph_calling_color(self.graph)
            if color == "red":
                self.emit("red_return")
            elif color == "gray":
                self.emit("gray_return")
            elif color == "yellow":
                self.emit("yellow_return")
            else:
                assert 0, "unknown graph calling color %s" % (color, )
        elif len(block.exits) == 1:
            link, = block.exits
            self.insert_renaming(link)
            self.make_bytecode_block(link.target, insert_goto=True)
        elif len(block.exits) == 2:
            linkfalse, linktrue = block.exits
            if linkfalse.llexitcase == True:
                linkfalse, linktrue = linktrue, linkfalse
            color = self.varcolor(block.exitswitch)
            index = self.serialize_oparg(color, block.exitswitch)
            reverse = None
            if color == "red":
                srcopname, srcargs = self.trace_back_bool_var(
                    block, block.exitswitch)
                if srcopname is not None:
                    if srcopname == 'ptr_nonzero':
                        reverse = False
                    elif srcopname == 'ptr_iszero':
                        reverse = True
            if reverse is not None:
                ptrindex = self.serialize_oparg("red", srcargs[0])
                self.emit("red_goto_ifptrnonzero")
                self.emit(reverse)
                self.emit(ptrindex)
            else:
                self.emit("%s_goto_iftrue" % color)
            self.emit(index)
            self.emit(tlabel(linktrue))
            self.insert_renaming(linkfalse)
            self.make_bytecode_block(linkfalse.target, insert_goto=True)
            self.emit(label(linktrue))
            self.insert_renaming(linktrue)
            self.make_bytecode_block(linktrue.target, insert_goto=True)
        else:
            XXX

    def insert_merges(self, block):
        if block is self.graph.returnblock:
            return
        if len(self.entrymap[block]) <= 1:
            return
        num = self.num_mergepoints
        self.num_mergepoints += 1
        # make keydesc
        key = ()
        for arg in self.sort_by_color(block.inputargs)[1]:
            TYPE = arg.concretetype
            key += (TYPE, )
        if not key:
            keyindex = -1 # use prebuilt empty_key
        elif key not in self.keydesc_positions:
            keyindex = len(self.keydesc_positions)
            self.keydesc_positions[key] = keyindex
            self.keydescs.append(KeyDesc(self.RGenOp, *key))
        else:
            keyindex = self.keydesc_positions[key]
        self.emit("merge")
        self.emit(num)
        self.emit(keyindex)

    def insert_renaming(self, link):
        reds, greens = self.sort_by_color(link.args, link.target.inputargs)
        for color, args in [("red", reds), ("green", greens)]:
            result = []
            for v in args:
                result.append(self.serialize_oparg(color, v))
            self.emit("make_new_%svars" % (color, ))
            self.emit(len(args))
            self.emit(*result)

    def serialize_op(self, op):
        specialcase = getattr(self, "serialize_op_%s" % (op.opname, ), None)
        if specialcase is not None:
            try:
                return specialcase(op)
            except NotImplementedError:
                pass
        color = self.opcolor(op)
        args = []
        for arg in op.args:
            args.append(self.serialize_oparg(color, arg))
        self.serialize_opcode(color, op)
        self.emit(*args)
        if self.hannotator.binding(op.result).is_green():
            self.register_greenvar(op.result)
        else:
            self.register_redvar(op.result)
        

    def serialize_opcode(self, color, op):
        opname = op.opname
        name = "%s_%s" % (color, opname)
        index = self.interpreter.find_opcode(name)
        if index == -1:
            opdesc = rtimeshift.make_opdesc(
                self.RGenOp, opname,
                [self.hannotator.binding(arg) for arg in op.args],
                self.hannotator.binding(op.result), )
            index = self.interpreter.make_opcode_implementation(color, opdesc)
        self.emit(name)

    def serialize_oparg(self, color, arg):
        if color == "red":
            if self.varcolor(arg) == "green":
                return self.convert_to_red(arg)
            return self.redvar_position(arg)
        elif color == "green":
            return self.green_position(arg)
        assert 0, "unknown color"

    def convert_to_red(self, arg):
        block = self.current_block
        if (arg, block) in self.redvar_positions:
            # already converted
            return self.redvar_positions[arg, block]
        self.emit("make_redbox")
        resultindex = self.register_redvar((arg, block))
        argindex = self.green_position(arg)
        self.emit(argindex)
        self.emit(self.type_position(arg.concretetype))
        return resultindex

    def opcolor(self, op):
        for v in op.args:
            if not self.hannotator.binding(v).is_green():
                return "red"
        if not self.hannotator.binding(op.result).is_green():
            return "red"
        return "green"

    def varcolor(self, var):
        if self.hannotator.binding(var).is_green():
            color = "green"
        else:
            color = "red"
        return color
        
    def register_redvar(self, arg, where=-1):
        assert arg not in self.redvar_positions
        if where == -1:
            where = self.free_red[self.current_block]
            self.free_red[self.current_block] += 1
        self.redvar_positions[arg] = where
        return where

    def redvar_position(self, arg):
        return self.redvar_positions[arg]

    def register_greenvar(self, arg, where=None):
        assert isinstance(arg, flowmodel.Variable)
        if where is None:
            where = self.free_green[self.current_block]
            self.free_green[self.current_block] += 1
        self.greenvar_positions[arg] = where
        return where

    def green_position(self, arg):
        if isinstance(arg, flowmodel.Variable):
            return self.greenvar_positions[arg]
        return ~self.const_position(arg)

    def const_position(self, const):
        if const in self.const_positions:
            return self.const_positions[const]
        const = self.RGenOp.constPrebuiltGlobal(const.value)
        result = len(self.constants)
        self.constants.append(const)
        self.const_positions[const] = result
        return result

    def type_position(self, TYPE):
        if TYPE in self.type_positions:
            return self.type_positions[TYPE]
        self.typekinds.append(self.RGenOp.kindToken(TYPE))
        self.redboxclasses.append(rvalue.ll_redboxcls(TYPE))
        result = len(self.type_positions)
        self.type_positions[TYPE] = result
        return result

    def structtypedesc_position(self, TYPE):
        if TYPE in self.structtypedesc_positions:
            return self.structtypedesc_positions[TYPE]
        self.structtypedescs.append(
            rcontainer.StructTypeDesc(self.RGenOp, TYPE))
        result = len(self.structtypedesc_positions)
        self.structtypedesc_positions[TYPE] = result
        return result

    def fielddesc_position(self, TYPE, fieldname):
        if (fieldname, TYPE) in self.fielddesc_positions:
            return self.fielddesc_positions[fieldname, TYPE]
        structtypedesc = rcontainer.StructTypeDesc(self.RGenOp, TYPE)
        fielddesc = structtypedesc.getfielddesc(fieldname)
        if fielddesc is None:
            self.fielddesc_positions[fieldname, TYPE] = -1
            return -1
        result = len(self.fielddescs)
        self.fielddescs.append(fielddesc)
        self.fielddesc_positions[fieldname, TYPE] = result
        return result

    def arrayfielddesc_position(self, TYPE):
        if TYPE in self.fielddesc_positions:
            return self.fielddesc_positions[TYPE]
        arrayfielddesc = rcontainer.ArrayFieldDesc(self.RGenOp, TYPE)
        result = len(self.arrayfielddescs)
        self.arrayfielddescs.append(arrayfielddesc)
        self.arrayfielddesc_positions[TYPE] = result
        return result

    def oopspecdesc_position(self, fnobj, canraise):
        key = fnobj, canraise
        if key in self.oopspecdesc_positions:
            return self.oopspecdesc_positions[key]
        oopspecdesc = oop.OopSpecDesc(self.RGenOp, self.rtyper,
                                      fnobj, canraise)
        result = len(self.oopspecdescs)
        self.oopspecdescs.append(oopspecdesc)
        self.oopspecdesc_positions[key] = result
        return result

    def graph_position(self, graph):
        if graph in self.graph_positions:
            return self.graph_positions[graph]
        if graph in self.all_graphs:
            bytecode = self.all_graphs[graph]
        else:
            bytecode = JitCode.__new__(JitCode)
            self.all_graphs[graph] = bytecode
            self.unfinished_graphs.append(graph)
        index = len(self.called_bytecodes)
        self.called_bytecodes.append(bytecode)
        self.graph_positions[graph] = index
        return index

    def nonrainbow_position(self, fnptr, *voidargs):
        fn = fnptr._obj
        key = fn, voidargs
        if key in self.nonrainbow_positions:
            return self.nonrainbow_positions[key]
        FUNCTYPE = lltype.typeOf(fn)
        argiter = unrolling_iterable(FUNCTYPE.ARGS)
        numargs = len(FUNCTYPE.ARGS)
        def call_normal_function(interpreter, greenargs):
            assert len(greenargs) + len(voidargs) == numargs 
            args = ()
            j = 0
            k = 0
            for ARG in argiter:
                if ARG == lltype.Void:
                    # XXX terrible hack
                    arg = voidargs[k]
                    if not we_are_translated():
                        arg._TYPE = lltype.Void
                    args += (arg, )
                    k += 1
                else:
                    genconst = greenargs[j]
                    arg = genconst.revealconst(ARG)
                    args += (arg, )
                    j += 1
            rgenop = interpreter.jitstate.curbuilder.rgenop
            try:
                result = rgenop.genconst(fnptr(*args))
            except Exception, e:
                XXX # need to create a default result and set exception
            interpreter.green_result(result)
        result = len(self.nonrainbow_functions)
        self.nonrainbow_functions.append(call_normal_function)
        self.nonrainbow_positions[key] = result
        return result

    def interiordesc(self, op, PTRTYPE, nb_offsets):
        path = []
        CONTAINER = PTRTYPE.TO
        indices_v = []
        for i in range(1, 1 + nb_offsets):
            varg = op.args[i]
            T = varg.concretetype
            if T is lltype.Void:
                fieldname = varg.value
                CONTAINER = getattr(CONTAINER, fieldname)
                path.append(fieldname)
            else:
                assert T is lltype.Signed
                CONTAINER = CONTAINER.OF
                path.append(None)    # placeholder for 'array index'
                indices_v.append(varg)
        if CONTAINER is lltype.Void:     # Void field
            return -1, None
        else:
            key = (PTRTYPE.TO, tuple(path))
            if key in self.interiordesc_positions:
                return self.interiordesc_positions[key]
            desc = rcontainer.InteriorDesc(self.RGenOp, PTRTYPE.TO, tuple(path))
            result = len(self.interiordescs)
            self.interiordescs.append(desc)
            return (result, indices_v)
        
    def emit(self, *stuff):
        assert stuff is not None
        for x in stuff:
            assert not isinstance(x, list)
            self.assembler.append(x)

    def sort_by_color(self, vars, by_color_of_vars=None):
        reds = []
        greens = []
        if by_color_of_vars is None:
            by_color_of_vars = vars
        for v, bcv in zip(vars, by_color_of_vars):
            if v.concretetype is lltype.Void:
                continue
            if self.hannotator.binding(bcv).is_green():
                greens.append(v)
            else:
                reds.append(v)
        return reds, greens

    # ____________________________________________________________
    # operation special cases

    def serialize_op_hint(self, op):
        hints = op.args[1].value
        arg = op.args[0]
        result = op.result
        if "concrete" in hints:
            assert self.hannotator.binding(arg).is_green()
            assert self.hannotator.binding(result).is_green()
            self.register_greenvar(result, self.green_position(arg))
            return
        if "variable" in hints:
            assert not self.hannotator.binding(result).is_green()
            if self.hannotator.binding(arg).is_green():
                resultindex = self.convert_to_red(arg)
                self.register_redvar(result, resultindex)
            else:
                self.register_redvar(result, self.redvar_position(arg))
            return
        if "deepfreeze" in hints:
            if self.varcolor(result) == "red":
                self.register_redvar(result, self.redvar_position(arg))
            else:
                self.register_greenvar(result, self.green_position(arg))
            return

    def args_of_call(self, args, colored_as):
        result = []
        reds, greens = self.sort_by_color(args, colored_as)
        result = []
        for color, args in [("green", greens), ("red", reds)]:
            result.append(len(args))
            for v in args:
                result.append(self.serialize_oparg(color, v))
        return result

    def serialize_op_debug_assert(self, op):
        pass

    def serialize_op_direct_call(self, op):
        kind, exc = self.guess_call_kind(op)
        print op, kind, exc
        if kind == "oopspec":
            from pypy.jit.timeshifter.oop import Index
            fnobj = op.args[0].value._obj
            oopspecdescindex = self.oopspecdesc_position(fnobj, exc)
            oopspecdesc = self.oopspecdescs[oopspecdescindex]
            opargs = op.args[1:]
            args_v = []
            args = []
            for obj in oopspecdesc.argtuple:
                if isinstance(obj, Index):
                    v = opargs[obj.n]
                else:
                    v = flowmodel.Constant(obj, lltype.typeOf(obj))
                args_v.append(v)
                args.append(self.serialize_oparg("red", v))

            ll_handler = oopspecdesc.ll_handler
            couldfold = oopspecdesc.couldfold
            missing_args = ((ll_handler.func_code.co_argcount - 3) -
                            len(oopspecdesc.argtuple))
            assert missing_args >= 0
            if missing_args > 0:
                assert (ll_handler.func_defaults[-missing_args:] ==
                        (None,) * missing_args)

            if oopspecdesc.is_method:
                hs_self = self.hannotator.binding(
                    opargs[oopspecdesc.argtuple[0].n])
                deepfrozen = hs_self.deepfrozen
            else:
                deepfrozen = False

            self.emit("red_oopspec_call_%s" % (len(args), ))
            self.emit(oopspecdescindex)
            self.emit(deepfrozen)
            self.emit(*args)
            self.register_redvar(op.result)
            return
        elif kind == "green":
            voidargs = [const.value for const in op.args[1:]
                            if const.concretetype == lltype.Void]
            pos = self.nonrainbow_position(op.args[0].value, *voidargs)
            emitted_args = []
            for v in op.args[1:]:
                if v.concretetype != lltype.Void:
                    emitted_args.append(self.serialize_oparg("green", v))
            self.emit("green_direct_call")
            self.emit(len(emitted_args))
            self.emit(*emitted_args)
            self.emit(pos)
            self.register_greenvar(op.result)
            return
        targets = dict(self.graphs_from(op))
        assert len(targets) == 1
        targetgraph, = targets.values()
        if kind == "red" or kind == "gray":
            graphindex = self.graph_position(targetgraph)
            args = targetgraph.getargs()
            emitted_args = self.args_of_call(op.args[1:], args)
            self.emit("red_direct_call")
            self.emit(*emitted_args)
            self.emit(graphindex)
            if kind == "red":
                self.register_redvar(op.result)
            self.emit("red_after_direct_call")
        elif kind == "yellow":
            graphindex = self.graph_position(targetgraph)
            args = targetgraph.getargs()
            emitted_args = self.args_of_call(op.args[1:], args)
            self.emit("yellow_direct_call")
            self.emit(*emitted_args)
            self.emit(graphindex)
            self.emit("yellow_after_direct_call")
            self.emit("yellow_retrieve_result")
            self.register_greenvar(op.result)
        else:
            XXX

    def serialize_op_indirect_call(self, op):
        XXX

    def serialize_op_malloc(self, op):
        index = self.structtypedesc_position(op.args[0].value)
        self.emit("red_malloc", index)
        self.register_redvar(op.result)

    def serialize_op_malloc_varsize(self, op):
        PTRTYPE = op.result.concretetype
        TYPE = PTRTYPE.TO
        v_size = op.args[2]
        sizeindex = self.serialize_oparg("red", v_size)
        if isinstance(TYPE, lltype.Struct):
            index = self.structtypedesc_position(op.args[0].value)
            self.emit("red_malloc_varsize_struct")
        else:
            index = self.arrayfielddesc_position(TYPE)
            self.emit("red_malloc_varsize_array")
        self.emit(index, sizeindex)
        self.register_redvar(op.result)

    def serialize_op_zero_gc_pointers_inside(self, op):
        pass # XXX is that right?

    def serialize_op_cast_pointer(self, op):
        color = self.varcolor(op.result)
        assert color == self.varcolor(op.args[0])
        if color == "green":
            self.register_greenvar(op.result, self.green_position(op.args[0]))
        else:
            self.register_redvar(op.result, self.redvar_position(op.args[0]))

    def serialize_op_keepalive(self, op):
        pass

    def serialize_op_getfield(self, op):
        assert self.opcolor(op) == "red"
        args = op.args
        if args[0] == self.exceptiondesc.cexcdata:
            # reading one of the exception boxes (exc_type or exc_value)
            fieldname = args[1].value
            if fieldname == 'exc_type':
                self.emit("read_exctype")
            elif fieldname == 'exc_value':
                self.emit("read_excvalue")
            else:
                raise Exception("getfield(exc_data, %r)" % (fieldname,))
            self.register_redvar(op.result)
            return

        # virtualizable access read
        PTRTYPE = args[0].concretetype
        if PTRTYPE.TO._hints.get('virtualizable', False):
            XXX

        # non virtual case                
        index = self.serialize_oparg("red", args[0])
        fieldname = args[1].value
        s_struct = self.hannotator.binding(args[0])
        deepfrozen = s_struct.deepfrozen
        
        fielddescindex = self.fielddesc_position(PTRTYPE.TO, fieldname)
        if fielddescindex == -1:   # Void field
            return
        self.emit("red_getfield", index, fielddescindex, deepfrozen)
        self.register_redvar(op.result)


    def serialize_op_setfield(self, op):
        args = op.args
        PTRTYPE = args[0].concretetype
        VALUETYPE = args[2].concretetype
        if VALUETYPE is lltype.Void:
            return
        if args[0] == self.exceptiondesc.cexcdata:
            # reading one of the exception boxes (exc_type or exc_value)
            fieldname = args[1].value
            val = self.serialize_oparg("red", args[2])
            if fieldname == 'exc_type':
                self.emit("write_exctype", val)
            elif fieldname == 'exc_value':
                self.emit("write_excvalue", val)
            else:
                raise Exception("getfield(exc_data, %r)" % (fieldname,))
            return
        # non virtual case                
        destboxindex = self.serialize_oparg("red", args[0])
        valboxindex = self.serialize_oparg("red", args[2])
        fieldname = args[1].value
        fielddescindex = self.fielddesc_position(PTRTYPE.TO, fieldname)
        if fielddescindex == -1:   # Void field
            return
        self.emit("red_setfield", destboxindex, fielddescindex, valboxindex)

    def serialize_op_getarrayitem(self, op):
        arrayvar, indexvar = op.args
        PTRTYPE = arrayvar.concretetype
        if PTRTYPE.TO.OF is lltype.Void:
            return
        deepfrozen = self.hannotator.binding(arrayvar).deepfrozen
        fielddescindex = self.arrayfielddesc_position(PTRTYPE.TO)
        arrayindex = self.serialize_oparg("red", arrayvar)
        index = self.serialize_oparg("red", indexvar)
        self.emit("red_getarrayitem", arrayindex, fielddescindex, index,
                  deepfrozen)
        self.register_redvar(op.result)

    def serialize_op_setarrayitem(self, op):
        args = op.args
        PTRTYPE = args[0].concretetype
        VALUETYPE = PTRTYPE.TO.OF
        if VALUETYPE is lltype.Void:
            return
        destboxindex = self.serialize_oparg("red", args[0])
        indexboxindex = self.serialize_oparg("red", args[1])
        valboxindex = self.serialize_oparg("red", args[2])
        fieldname = args[1].value
        fielddescindex = self.arrayfielddesc_position(PTRTYPE.TO)
        if fielddescindex == -1:   # Void field
            return
        self.emit("red_setarrayitem", destboxindex, fielddescindex,
                  indexboxindex, valboxindex)

    def serialize_op_getarraysize(self, op):
        arrayvar, = op.args
        PTRTYPE = arrayvar.concretetype
        if PTRTYPE.TO.OF is lltype.Void:
            return
        fielddescindex = self.arrayfielddesc_position(PTRTYPE.TO)
        arrayindex = self.serialize_oparg("red", arrayvar)
        self.emit("red_getarraysize", arrayindex, fielddescindex)
        self.register_redvar(op.result)

    def serialize_op_getinteriorfield(self, op):
        color = self.opcolor(op)
        structvar = op.args[0]
        PTRTYPE = structvar.concretetype
        # no virtualizable access read here
        assert not PTRTYPE.TO._hints.get('virtualizable', False)

        # non virtual case
        interiordescindex, indices_v = self.interiordesc(
                op, PTRTYPE, len(op.args) - 1)
        if interiordescindex == -1:    # Void field
            return None
        structindex = self.serialize_oparg("red", structvar)
        deepfrozen = self.hannotator.binding(structvar).deepfrozen
        indexes = []
        for arg in indices_v:
            indexes.append(self.serialize_oparg("red", arg))
        self.emit("%s_getinteriorfield" % color, structindex,
                  interiordescindex, deepfrozen)
        self.emit(len(indexes))
        self.emit(*indexes)
        if color == "red":
            self.register_redvar(op.result)
        else:
            self.register_greenvar(op.result)

    def serialize_op_setinteriorfield(self, op):
        structvar = op.args[0]
        valuevar = op.args[-1]
        PTRTYPE = structvar.concretetype
        # non virtual case
        interiordescindex, indices_v = self.interiordesc(
                op, PTRTYPE, len(op.args) - 2)
        structindex = self.serialize_oparg("red", structvar)
        indexes = []
        for arg in indices_v:
            indexes.append(self.serialize_oparg("red", arg))
        valueindex = self.serialize_oparg("red", valuevar)
        self.emit("red_setinteriorfield", structindex, interiordescindex)
        self.emit(len(indexes))
        self.emit(*indexes)
        self.emit(valueindex)

    def serialize_op_getinteriorarraysize(self, op):
        structvar = op.args[0]
        PTRTYPE = structvar.concretetype
        color = self.opcolor(op)
        # non virtual case
        interiordescindex, indices_v = self.interiordesc(
                op, PTRTYPE, len(op.args) - 1)
        assert interiordescindex != -1
        structindex = self.serialize_oparg("red", structvar)
        indexes = []
        for arg in indices_v:
            indexes.append(self.serialize_oparg("red", arg))
        self.emit("%s_getinteriorarraysize" % color, structindex,
                  interiordescindex)
        self.emit(len(indexes))
        self.emit(*indexes)
        if color == "red":
            self.register_redvar(op.result)
        else:
            self.register_greenvar(op.result)


    # call handling

    def graphs_from(self, spaceop):
        if spaceop.opname == 'direct_call':
            c_func = spaceop.args[0]
            fnobj = c_func.value._obj
            graphs = [fnobj.graph]
            args_v = spaceop.args[1:]
        elif spaceop.opname == 'indirect_call':
            graphs = spaceop.args[-1].value
            if graphs is None:
                return       # cannot follow at all
            args_v = spaceop.args[1:-1]
        else:
            raise AssertionError(spaceop.opname)
        # if the graph - or all the called graphs - are marked as "don't
        # follow", directly return None as a special case.  (This is only
        # an optimization for the indirect_call case.)
        for graph in graphs:
            if self.hannotator.policy.look_inside_graph(graph):
                break
        else:
            return
        for graph in graphs:
            tsgraph = self.specialized_graph_of(graph, args_v, spaceop.result)
            yield graph, tsgraph

    def trace_back_bool_var(self, block, v):
        """Return the (opname, arguments) that created the exitswitch of
        the block.  The opname is None if not found.
        """
        inverted = False
        for i in range(len(block.operations)-1, -1, -1):
            op = block.operations[i]
            if op.result is v:
                if op.opname == 'bool_not':
                    inverted = not inverted
                    [v] = op.args
                elif op.opname == 'same_as':
                    [v] = op.args
                else:
                    opname = op.opname
                    opargs = op.args
                    if inverted:
                        opname = {'ptr_nonzero': 'ptr_iszero',
                                  'ptr_iszero' : 'ptr_nonzero'}.get(opname)
                    return opname, opargs    # found
        # not found, comes from earlier block - give up
        return None, None

    def guess_call_kind(self, spaceop):
        if spaceop.opname == 'direct_call':
            c_func = spaceop.args[0]
            fnobj = c_func.value._obj
            if hasattr(fnobj, 'jitcallkind'):
                return fnobj.jitcallkind, None
            if (hasattr(fnobj._callable, 'oopspec') and
                self.hannotator.policy.oopspec):
                if fnobj._callable.oopspec.startswith('vable.'):
                    return 'vable', None
                hs_result = self.hannotator.binding(spaceop.result)
                if (hs_result.is_green() and
                    hs_result.concretetype is not lltype.Void):
                    return 'green', self.can_raise(spaceop)
                return 'oopspec', self.can_raise(spaceop)
        if self.hannotator.bookkeeper.is_green_call(spaceop):
            return 'green', None
        withexc = self.can_raise(spaceop)
        colors = {}
        for graph, tsgraph in self.graphs_from(spaceop):
            color = self.graph_calling_color(tsgraph)
            colors[color] = tsgraph
        if not colors: # cannot follow this call
            return 'residual', withexc
        assert len(colors) == 1, colors   # buggy normalization?
        return color, withexc

    def specialized_graph_of(self, graph, args_v, v_result):
        bk = self.hannotator.bookkeeper
        args_hs = [self.hannotator.binding(v) for v in args_v]
        hs_result = self.hannotator.binding(v_result)
        if isinstance(hs_result, hintmodel.SomeLLAbstractConstant):
            fixed = hs_result.is_fixed()
        else:
            fixed = False
        specialization_key = bk.specialization_key(fixed, args_hs)
        special_graph = bk.get_graph_by_key(graph, specialization_key)
        return special_graph

    def graph_calling_color(self, graph):
        hs_res = self.hannotator.binding(graph.getreturnvar())
        if originalconcretetype(hs_res) is lltype.Void:
            c = 'gray'
        elif hs_res.is_green():
            c = 'yellow'
        else:
            c = 'red'
        return c


class label(object):
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return "label(%r)" % (self.name, )

class tlabel(object):
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return "tlabel(%r)" % (self.name, )

def assemble(interpreter, *args):
    result = []
    labelpos = {}
    def emit_2byte(index):
        result.append(chr((index >> 8) & 0xff))
        result.append(chr(index & 0xff))
    for arg in args:
        if isinstance(arg, str):
            opcode = interpreter.find_opcode(arg)
            assert opcode >= 0, "unknown opcode %s" % (arg, )
            emit_2byte(opcode)
        elif isinstance(arg, bool):
            result.append(chr(int(arg)))
        elif isinstance(arg, int):
            emit_2byte(arg)
        elif isinstance(arg, label):
            labelpos[arg.name] = len(result)
        elif isinstance(arg, tlabel):
            result.extend((arg, None, None, None))
        else:
            assert "don't know how to emit %r" % (arg, )
    for i in range(len(result)):
        b = result[i]
        if isinstance(b, tlabel):
            for j in range(1, 4):
                assert result[i + j] is None
            index = labelpos[b.name]
            result[i + 0] = chr((index >> 24) & 0xff)
            result[i + 1] = chr((index >> 16) & 0xff)
            result[i + 2] = chr((index >>  8) & 0xff)
            result[i + 3] = chr(index & 0xff)
    return "".join(result)
