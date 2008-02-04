from pypy.rlib.rarithmetic import intmask
from pypy.rlib.unroll import unrolling_iterable
from pypy.objspace.flow import model as flowmodel
from pypy.rpython.lltypesystem import lltype
from pypy.jit.hintannotator.model import originalconcretetype
from pypy.jit.hintannotator import model as hintmodel
from pypy.jit.timeshifter import rtimeshift, rvalue
from pypy.jit.timeshifter.greenkey import KeyDesc, empty_key, GreenKey
from pypy.translator.backendopt.removenoops import remove_same_as

class JitCode(object):
    """
    normal operations have the following format:
    2 byte - operation
    n * 2 byte - arguments
    
    for nonvoid results the result is appended to the varlist

    red vars are just indexes
    green vars are positive indexes
    green consts are negative indexes
    """

    def __init__(self, name, code, constants, typekinds, redboxclasses,
                 keydescs, called_bytecodes, num_mergepoints, graph_color,
                 nonrainbow_functions, is_portal):
        self.name = name
        self.code = code
        self.constants = constants
        self.typekinds = typekinds
        self.redboxclasses = redboxclasses
        self.keydescs = keydescs
        self.called_bytecodes = called_bytecodes
        self.num_mergepoints = num_mergepoints
        self.graph_color = graph_color
        self.nonrainbow_functions = nonrainbow_functions
        self.is_portal = is_portal

    def _freeze_(self):
        return True

SIGN_EXTEND2 = 1 << 15

class STOP(object):
    pass
STOP = STOP()

class JitInterpreter(object):
    def __init__(self):
        self.opcode_implementations = []
        self.opcode_descs = []
        self.opname_to_index = {}
        self.jitstate = None
        self.queue = None
        self._add_implemented_opcodes()

    def run(self, jitstate, bytecode, greenargs, redargs,
            start_bytecode_loop=True):
        self.jitstate = jitstate
        self.queue = rtimeshift.DispatchQueue(bytecode.num_mergepoints)
        rtimeshift.enter_frame(self.jitstate, self.queue)
        self.frame = self.jitstate.frame
        self.frame.pc = 0
        self.frame.bytecode = bytecode
        self.frame.local_boxes = redargs
        self.frame.local_green = greenargs
        if start_bytecode_loop:
            self.bytecode_loop()
        return self.jitstate

    def bytecode_loop(self):
        while 1:
            bytecode = self.load_2byte()
            assert bytecode >= 0
            result = self.opcode_implementations[bytecode](self)
            if result is STOP:
                return
            else:
                assert result is None

    def dispatch(self):
        is_portal = self.frame.bytecode.is_portal
        graph_color = self.frame.bytecode.graph_color
        queue = self.queue
        newjitstate = rtimeshift.dispatch_next(queue)
        resumepoint = rtimeshift.getresumepoint(newjitstate)
        self.newjitstate(newjitstate)
        if resumepoint == -1:
            if graph_color == "red":
                newjitstate = rtimeshift.leave_graph_red(
                        queue, is_portal)
            elif graph_color == "yellow":
                newjitstate = rtimeshift.leave_graph_yellow(queue)
            elif graph_color == "green":
                XXX
            elif graph_color == "gray":
                assert not is_portal
                newjitstate = rtimeshift.leave_graph_gray(queue)
            else:
                assert 0, "unknown graph color %s" % (graph_color, )

            self.newjitstate(newjitstate)
            if self.frame is None:
                return STOP
        else:
            self.frame.pc = resumepoint

    # operation helper functions

    def load_2byte(self):
        pc = self.frame.pc
        assert pc >= 0
        result = ((ord(self.frame.bytecode.code[pc]) << 8) |
                   ord(self.frame.bytecode.code[pc + 1]))
        self.frame.pc = pc + 2
        return intmask((result ^ SIGN_EXTEND2) - SIGN_EXTEND2)

    def load_4byte(self):
        pc = self.frame.pc
        assert pc >= 0
        result = ((ord(self.frame.bytecode.code[pc + 0]) << 24) |
                  (ord(self.frame.bytecode.code[pc + 1]) << 16) |
                  (ord(self.frame.bytecode.code[pc + 2]) <<  8) |
                  (ord(self.frame.bytecode.code[pc + 3]) <<  0))
        self.frame.pc = pc + 4
        return intmask(result)

    def get_greenarg(self):
        i = self.load_2byte()
        if i < 0:
            return self.frame.bytecode.constants[~i]
        return self.frame.local_green[i]

    def get_green_varargs(self):
        greenargs = []
        num = self.load_2byte()
        for i in range(num):
            greenargs.append(self.get_greenarg())
        return greenargs

    def get_red_varargs(self):
        redargs = []
        num = self.load_2byte()
        for i in range(num):
            redargs.append(self.get_redarg())
        return redargs

    def get_redarg(self):
        return self.frame.local_boxes[self.load_2byte()]

    def red_result(self, box):
        self.frame.local_boxes.append(box)

    def green_result(self, gv):
        self.frame.local_green.append(gv)

    def newjitstate(self, newjitstate):
        self.jitstate = newjitstate
        self.queue = None
        if newjitstate is not None:
            frame = newjitstate.frame
            self.frame = frame
            if frame is not None:
                self.queue = frame.dispatchqueue
        else:
            self.frame = None

    # operation implementations
    def opimpl_make_redbox(self):
        genconst = self.get_greenarg()
        typeindex = self.load_2byte()
        kind = self.frame.bytecode.typekinds[typeindex]
        redboxcls = self.frame.bytecode.redboxclasses[typeindex]
        self.red_result(redboxcls(kind, genconst))

    def opimpl_goto(self):
        target = self.load_4byte()
        self.frame.pc = target

    def opimpl_green_goto_iftrue(self):
        genconst = self.get_greenarg()
        target = self.load_4byte()
        arg = genconst.revealconst(lltype.Bool)
        if arg:
            self.frame.pc = target

    def opimpl_red_goto_iftrue(self):
        switchbox = self.get_redarg()
        target = self.load_4byte()
        # XXX not sure about passing no green vars
        descision = rtimeshift.split(self.jitstate, switchbox, self.frame.pc)
        if descision:
            self.frame.pc = target

    def opimpl_red_return(self):
        rtimeshift.save_return(self.jitstate)
        return self.dispatch()

    def opimpl_gray_return(self):
        rtimeshift.save_return(self.jitstate)
        return self.dispatch()

    def opimpl_yellow_return(self):
        # save the greens to make the return value findable by collect_split
        rtimeshift.save_greens(self.jitstate, self.frame.local_green)
        rtimeshift.save_return(self.jitstate)
        return self.dispatch()

    def opimpl_make_new_redvars(self):
        self.frame.local_boxes = self.get_red_varargs()

    def opimpl_make_new_greenvars(self):
        # an opcode with a variable number of args
        # num_args arg_old_1 arg_new_1 ...
        num = self.load_2byte()
        if num == 0 and len(self.frame.local_green) == 0:
            # fast (very common) case
            return
        newgreens = []
        for i in range(num):
            newgreens.append(self.get_greenarg())
        self.frame.local_green = newgreens

    def opimpl_merge(self):
        mergepointnum = self.load_2byte()
        keydescnum = self.load_2byte()
        if keydescnum == -1:
            key = empty_key
        else:
            keydesc = self.frame.bytecode.keydescs[keydescnum]
            key = GreenKey(self.frame.local_green[:keydesc.nb_vals], keydesc)
        states_dic = self.queue.local_caches[mergepointnum]
        done = rtimeshift.retrieve_jitstate_for_merge(states_dic, self.jitstate,
                                                      key, None)
        if done:
            return self.dispatch()

    def opimpl_red_direct_call(self):
        greenargs = self.get_green_varargs()
        redargs = self.get_red_varargs()
        bytecodenum = self.load_2byte()
        targetbytecode = self.frame.bytecode.called_bytecodes[bytecodenum]
        self.run(self.jitstate, targetbytecode, greenargs, redargs,
                 start_bytecode_loop=False)
        # this frame will be resumed later in the next bytecode, which is
        # red_after_direct_call

    def opimpl_red_after_direct_call(self):
        newjitstate = rtimeshift.collect_split(
            self.jitstate, self.frame.pc,
            self.frame.local_green)
        assert newjitstate is self.jitstate

    def opimpl_green_direct_call(self):
        greenargs = self.get_green_varargs()
        redargs = self.get_red_varargs()
        index = self.load_2byte()
        function = self.frame.bytecode.nonrainbow_functions[index]
        function(self, greenargs, redargs)

    def opimpl_yellow_direct_call(self):
        greenargs = self.get_green_varargs()
        redargs = self.get_red_varargs()
        bytecodenum = self.load_2byte()
        targetbytecode = self.frame.bytecode.called_bytecodes[bytecodenum]
        self.run(self.jitstate, targetbytecode, greenargs, redargs,
                 start_bytecode_loop=False)
        # this frame will be resumed later in the next bytecode, which is
        # yellow_after_direct_call

    def opimpl_yellow_after_direct_call(self):
        newjitstate = rtimeshift.collect_split(
            self.jitstate, self.frame.pc,
            self.frame.local_green)
        assert newjitstate is self.jitstate

    def opimpl_yellow_retrieve_result(self):
        # XXX all this jitstate.greens business is a bit messy
        self.green_result(self.jitstate.greens[0])


    # ____________________________________________________________
    # construction-time interface

    def _add_implemented_opcodes(self):
        for name in dir(self):
            if not name.startswith("opimpl_"):
                continue
            opname = name[len("opimpl_"):]
            self.opname_to_index[opname] = len(self.opcode_implementations)
            self.opcode_implementations.append(getattr(self, name).im_func)
            self.opcode_descs.append(None)

    def find_opcode(self, name):
        return self.opname_to_index.get(name, -1)

    def make_opcode_implementation(self, color, opdesc):
        numargs = unrolling_iterable(range(opdesc.nb_args))
        if color == "green":
            def implementation(self):
                args = (opdesc.RESULT, )
                for i in numargs:
                    genconst = self.get_greenarg()
                    arg = genconst.revealconst(opdesc.ARGS[i])
                    args += (arg, )
                rgenop = self.jitstate.curbuilder.rgenop
                result = rgenop.genconst(opdesc.llop(*args))
                self.green_result(result)
        elif color == "red":
            if opdesc.nb_args == 1:
                impl = rtimeshift.ll_gen1
            elif opdesc.nb_args == 2:
                impl = rtimeshift.ll_gen2
            else:
                XXX
            def implementation(self):
                args = (opdesc, self.jitstate, )
                for i in numargs:
                    args += (self.get_redarg(), )
                result = impl(*args)
                self.red_result(result)
        else:
            assert 0, "unknown color"
        implementation.func_name = "opimpl_%s_%s" % (color, opdesc.opname)
        opname = "%s_%s" % (color, opdesc.opname)
        index = self.opname_to_index[opname] = len(self.opcode_implementations)
        self.opcode_implementations.append(implementation)
        self.opcode_descs.append(opdesc)
        return index




class BytecodeWriter(object):
    def __init__(self, t, hannotator, RGenOp):
        self.translator = t
        self.annotator = t.annotator
        self.hannotator = hannotator
        self.interpreter = JitInterpreter()
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
        # mapping tuple of green TYPES to index
        self.keydesc_positions = {}
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
            color = self.varcolor(returnvar)
            if color == "red":
                self.emit("red_return")
            elif originalconcretetype(returnvar) == lltype.Void:
                self.emit("gray_return")
            elif color == "green": # really a yellow call # XXX use graphcolor
                self.emit("yellow_return")
            else:
                XXX
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
            self.emit(result)

    def serialize_op(self, op):
        specialcase = getattr(self, "serialize_op_%s" % (op.opname, ), None)
        if specialcase is not None:
            return specialcase(op)
        color = self.opcolor(op)
        args = []
        for arg in op.args:
            args.append(self.serialize_oparg(color, arg))
        self.serialize_opcode(color, op)
        self.emit(args)
        if self.hannotator.binding(op.result).is_green():
            self.register_greenvar(op.result)
        else:
            self.register_redvar(op.result)
        

    def serialize_opcode(self, color, op):
        opname = op.opname
        name = "%s_%s" % (color, opname)
        index = self.interpreter.find_opcode(name)
        if index == -1:
            hop = PseudoHOP(
                op, [self.hannotator.binding(arg) for arg in op.args],
                self.hannotator.binding(op.result), self.RGenOp)
            opdesc = rtimeshift.make_opdesc(hop)
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

    def register_greenvar(self, arg, where=-1):
        assert isinstance(arg, flowmodel.Variable)
        if where == -1:
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

    def nonrainbow_position(self, fnptr):
        fn = fnptr._obj
        if fn in self.nonrainbow_positions:
            return self.nonrainbow_positions[fn]
        FUNCTYPE = lltype.typeOf(fn)
        argiter = unrolling_iterable(enumerate(FUNCTYPE.ARGS))
        numargs = len(FUNCTYPE.ARGS)
        def call_normal_function(interpreter, greenargs, redargs):
            assert len(redargs) == 0
            assert len(greenargs) == numargs
            args = ()
            for i, ARG in argiter:
                genconst = greenargs[i]
                arg = genconst.revealconst(ARG)
                args += (arg, )
            rgenop = interpreter.jitstate.curbuilder.rgenop
            result = rgenop.genconst(fnptr(*args))
            interpreter.green_result(result)
        result = len(self.nonrainbow_functions)
        self.nonrainbow_functions.append(call_normal_function)
        self.nonrainbow_positions[fn] = result
        return result
        
    def emit(self, stuff):
        assert stuff is not None
        if isinstance(stuff, list):
            self.assembler.extend(stuff)
        else:
            self.assembler.append(stuff)

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
        XXX

    def args_of_call(self, args, colored_as):
        result = []
        reds, greens = self.sort_by_color(args, colored_as)
        result = []
        for color, args in [("green", greens), ("red", reds)]:
            result.append(len(args))
            for v in args:
                result.append(self.serialize_oparg(color, v))
        return result

    def serialize_op_direct_call(self, op):
        targets = dict(self.graphs_from(op))
        assert len(targets) == 1
        targetgraph, = targets.values()
        kind, exc = self.guess_call_kind(op)
        if kind == "red" or kind == "gray":
            graphindex = self.graph_position(targetgraph)
            args = targetgraph.getargs()
            emitted_args = self.args_of_call(op.args[1:], args)
            self.emit("red_direct_call")
            self.emit(emitted_args)
            self.emit(graphindex)
            if kind == "red":
                self.register_redvar(op.result)
            self.emit("red_after_direct_call")
        elif kind == "green":
            pos = self.nonrainbow_position(op.args[0].value)
            args = targetgraph.getargs()
            emitted_args = self.args_of_call(op.args[1:], args)
            self.emit("green_direct_call")
            self.emit(emitted_args)
            self.emit(pos)
            self.register_greenvar(op.result)
        elif kind == "yellow":
            graphindex = self.graph_position(targetgraph)
            args = targetgraph.getargs()
            emitted_args = self.args_of_call(op.args[1:], args)
            self.emit("yellow_direct_call")
            self.emit(emitted_args)
            self.emit(graphindex)
            self.emit("yellow_after_direct_call")
            self.emit("yellow_retrieve_result")
            self.register_greenvar(op.result)
        else:
            XXX

    def serialize_op_indirect_call(self, op):
        XXX

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
        elif isinstance(arg, int):
            emit_2byte(arg)
        elif isinstance(arg, label):
            labelpos[arg.name] = len(result)
        elif isinstance(arg, tlabel):
            result.extend((arg, None, None, None))
        else:
            XXX
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



# XXX too lazy to fix the interface of make_opdesc, ExceptionDesc
class PseudoHOP(object):
    def __init__(self, op, args_s, s_result, RGenOp):
        self.spaceop = op
        self.args_s = args_s
        self.s_result = s_result
        self.rtyper = PseudoHRTyper(RGenOp=RGenOp)

class PseudoHRTyper(object):
    def __init__(self, **args):
        self.__dict__.update(**args)

