from pypy.objspace.flow import model as flowmodel
from pypy.rpython.lltypesystem import lltype
from pypy.jit.hintannotator.model import originalconcretetype
from pypy.jit.timeshifter import rtimeshift, rvalue
from pypy.rlib.unroll import unrolling_iterable

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

    def __init__(self, code, constants):
        self.code = code
        self.constants = constants

    def _freeze_(self):
        return True

class JitInterpreter(object):
    def __init__(self):
        self.opcode_implementations = []
        self.opcode_descs = []
        self.opname_to_index = {}
        self.jitstate = None
        self.bytecode = None
        self._add_implemented_opcodes()

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
                args = ()
                for i in numargs:
                    args.append(self.get_greenarg())
                result = opdesc.llop(*args)
                self.green_result(result)
        elif color == "red":
            if opdesc.nb_args == 1:
                impl = rtimeshift.ll_gen1
            elif opdesc.nb_args == 2:
                impl = rtimeshift.ll_gen2
            else:
                XXX
            def implementation(self):
                args = (self.jitstate, )
                for i in numargs:
                    args.append(self.get_redarg())
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
            

    # operation implemetations
    def opimpl_make_redbox(self):
        XXX

    def opimpl_goto(self):
        XXX

    def opimpl_green_goto_iftrue(self):
        XXX

    def opimpl_red_goto_iftrue(self):
        XXX

    def opimpl_red_return(self):
        XXX

    def opimpl_green_return(self):
        XXX

    def opimpl_make_new_redvars(self):
        # an opcode with a variable number of args
        # num_args arg_old_1 arg_new_1 ...
        XXX

    def opimpl_make_new_greenvars(self):
        # an opcode with a variable number of args
        # num_args arg_old_1 arg_new_1 ...
        XXX


class BytecodeWriter(object):
    def __init__(self, t, hintannotator, RGenOp):
        self.translator = t
        self.annotator = t.annotator
        self.hannotator = hintannotator
        self.interpreter = JitInterpreter()
        self.RGenOp = RGenOp

    def make_bytecode(self, graph):
        self.seen_blocks = {}
        self.bytecode = []
        self.constants = []
        self.const_positions = {}
        self.block_positions = {}
        self.additional_positions = {}
        self.graph = graph
        self.entrymap = flowmodel.mkentrymap(graph)
        self.make_bytecode_block(graph.startblock)
        self.patch_jumps()
        return JitCode("".join(self.bytecode), self.constants)

    def make_bytecode_block(self, block, insert_goto=False):
        if block in self.block_positions:
            if insert_goto:
                self.emit_2byte(self.interpreter.find_opcode("goto"))
                self.emit_4byte(self.block_positions[block])
            return
        # inserting a goto not necessary, falling through
        self.current_block = block
        self.redvar_positions = {}
        self.greenvar_positions = {}
        self.block_positions[block] = len(self.bytecode)
        reds, greens = self.sort_by_color(block.inputargs)
        # asign positions to the arguments
        for arg in reds:
            self.redvar_position(arg)
        for arg in greens:
            self.greenvar_positions(arg)
        #self.insert_merges(block)
        for op in block.operations:
            self.serialize_op(op)
        #self.insert_splits(block)
        self.insert_exits(block)

    def insert_exits(self, block):
        if block.exits == ():
            returnvar, = block.inputargs
            color = self.varcolor(returnvar)
            index = self.serialize_oparg(color, returnvar)
            self.emit_2byte(self.interpreter.find_opcode("%s_return" % color))
            self.emit_2byte(index)
        elif len(block.exits) == 1:
            link, = block.exits
            self.insert_renaming(link.args)
            self.make_bytecode_block(link.target, insert_goto=True)
        elif len(block.exits) == 2:
            linkfalse, linktrue = block.exits
            if linkfalse.llexitcase == True:
                linkfalse, linktrue = linktrue, linkfalse
            color = self.varcolor(block.exitswitch)
            index = self.serialize_oparg(color, block.exitswitch)
            self.emit_2byte(self.interpreter.find_opcode("%s_goto_iftrue" % color))
            self.emit_2byte(index)
            self.emit_jumptarget(linktrue)
            self.insert_renaming(linkfalse.args)
            self.make_bytecode_block(linkfalse.target, insert_goto=True)
            self.additional_positions[linktrue] = len(self.bytecode)
            self.insert_renaming(linktrue.args)
            self.emit_2byte(self.interpreter.find_opcode("goto"))
            self.emit_jumptarget(linktrue.target)
        else:
            XXX

    def patch_jumps(self):
        for i in range(len(self.bytecode)):
            byte = self.bytecode[i]
            if isinstance(self.bytecode[i], str):
                continue
            if byte in self.block_positions:
                index = self.block_positions[byte]
            else:
                index = self.additional_positions[byte]
            self.bytecode[i + 0] = chr((index >> 24) & 0xff)
            self.bytecode[i + 1] = chr((index >> 16) & 0xff)
            self.bytecode[i + 2] = chr((index >>  8) & 0xff)
            self.bytecode[i + 3] = chr(index & 0xff)


    def insert_renaming(self, args):
        reds, greens = self.sort_by_color(args)
        for color, args in [("red", reds), ("green", greens)]:
            result = []
            for v in args:
                result.append(self.serialize_oparg(color, v))
            self.emit_2byte(self.interpreter.find_opcode(
                "make_new_%svars" % (color, )))
            self.emit_2byte(len(args))
            for index in result:
                self.emit_2byte(index)

    def serialize_op(self, op):
        color = self.opcolor(op)
        args = []
        for arg in op.args:
            args.append(self.serialize_oparg(color, arg))
        self.serialize_opcode(color, op)
        for index in args:
            self.emit_2byte(index)
        if self.hannotator.binding(op.result).is_green():
            self.green_position(op.result)
        else:
            self.redvar_position(op.result)
        

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
        self.emit_2byte(index)

    def serialize_oparg(self, color, arg):
        if color == "red":
            if self.hannotator.binding(arg).is_green():
                return self.convert_to_red(arg)
            return self.redvar_position(arg)
        XXX

    def convert_to_red(self, arg):
        if arg in self.redvar_positions:
            # already converted
            return self.redvar_positions[arg]
        self.emit_2byte(self.interpreter.find_opcode("make_redbox"))
        resultindex = self.redvar_positions[arg] = len(self.redvar_positions)
        argindex = self.green_position(arg)
        self.emit_2byte(resultindex)
        self.emit_2byte(argindex)
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
        
    def redvar_position(self, arg):
        return self.redvar_positions.setdefault(
                    arg, len(self.redvar_positions))
        
    def green_position(self, arg):
        if isinstance(arg, flowmodel.Variable):
            return self.greenvar_positions.setdefault(
                        arg, len(self.greenvar_positions))
        return -self.const_positions(arg)

    def const_position(self, const):
        if const in self.const_position:
            return self.const_position[const]
        XXX
        
    def emit_2byte(self, index):
        assert not index & 0xffff0000
        self.bytecode.append(chr((index >> 8) & 0xff))
        self.bytecode.append(chr(index & 0xff))

    def emit_4byte(self, index):
        self.bytecode.append(chr((index >> 24) & 0xff))
        self.bytecode.append(chr((index >> 16) & 0xff))
        self.bytecode.append(chr((index >>  8) & 0xff))
        self.bytecode.append(chr(index & 0xff))

    def emit_jumptarget(self, block):
        self.bytecode.extend((block, None, None, None))

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

# XXX too lazy to fix the interface of make_opdesc
class PseudoHOP(object):
    def __init__(self, op, args_s, s_result, RGenOp):
        self.spaceop = op
        self.args_s = args_s
        self.s_result = s_result
        self.rtyper = PseudoHRTyper(RGenOp)

class PseudoHRTyper(object):
    def __init__(self, RGenOp):
        self.RGenOp = RGenOp

