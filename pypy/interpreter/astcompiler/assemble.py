"""
Python control flow graph generation and bytecode assembly.
"""

from pypy.interpreter.astcompiler import ast2 as ast, symtable
from pypy.interpreter import pycode
from pypy.tool import stdlib_opcode as ops

from pypy.interpreter.error import OperationError
from pypy.rlib.objectmodel import we_are_translated


class Instruction(object):

    def __init__(self, opcode, lineno, arg=0):
        assert lineno != -1
        self.opcode = opcode
        self.arg = arg
        self.lineno = lineno
        self.jump = None

    def size(self):
        if self.opcode >= ops.HAVE_ARGUMENT:
            if self.arg > 0xFFFF:
                return 6
            else:
                return 3
        else:
            return 1

    def jump_to(self, target, absolute=False):
        self.jump = (target, absolute)


    def __repr__(self):
        data = [ops.opname[self.opcode]]
        template = "<%s"
        if self.opcode >= ops.HAVE_ARGUMENT:
            data.append(self.arg)
            template += " %i"
            if self.jump:
                data.append(self.jump[0])
                template += " %s"
        template += ">"
        return template % tuple(data)


class Block(object):

    def __init__(self):
        self.instructions = []
        self.next_block = None
        self.marked = False
        self.have_return = False

    def _post_order(self, blocks):
        if self.marked:
            return
        self.marked = True
        if self.next_block is not None:
            self.next_block._post_order(blocks)
        for instr in self.instructions:
            if instr.jump:
                instr.jump[0]._post_order(blocks)
        blocks.append(self)
        self.marked = True

    def post_order(self):
        blocks = []
        self._post_order(blocks)
        blocks.reverse()
        return blocks

    def code_size(self):
        i = 0
        for instr in self.instructions:
            i += instr.size()
        return i

    def get_code(self):
        code = []
        for instr in self.instructions:
            opcode = instr.opcode
            if opcode >= ops.HAVE_ARGUMENT:
                arg = instr.arg
                if instr.arg > 0xFFFF:
                    ext = arg >> 16
                    code.append(chr(ops.EXTENDED_ARG))
                    code.append(chr(ext & 0xFF))
                    code.append(chr(ext >> 8))
                    arg &= 0xFFFF
                code.append(chr(opcode))
                code.append(chr(arg & 0xFF))
                code.append(chr(arg >> 8))
            else:
                code.append(chr(opcode))
        return ''.join(code)


def _make_index_dict_filter(syms, flag):
    i = 0
    result = {}
    for name, scope in syms.iteritems():
        if scope == flag:
            result[name] = i
            i += 1
    return result

def _list_to_dict(l, offset=0):
    result = {}
    index = offset
    for i in range(len(l)):
        result[l[i]] = index
        index += 1
    return result


class PythonCodeMaker(ast.ASTVisitor):

    def __init__(self, space, name, first_lineno, scope, compile_info):
        self.space = space
        self.name = name
        self.first_lineno = first_lineno
        self.compile_info = compile_info
        self.lineno = -1
        self.first_block = self.new_block()
        self.use_block(self.first_block)
        self.names = {}
        self.var_names = _list_to_dict(scope.varnames)
        self.cell_vars = _make_index_dict_filter(scope.symbols,
                                                 symtable.SCOPE_CELL)
        self.free_vars = _list_to_dict(scope.free_vars, len(self.cell_vars))
        self.w_consts = space.newdict()
        self.argcount = 0
        self.add_none_to_final_return = True

    def new_block(self):
        return Block()

    def use_block(self, block):
        self.current_block = block
        self.instrs = block.instructions

    def use_next_block(self, block=None):
        if block is None:
            block = self.new_block()
        self.current_block.next_block = block
        self.use_block(block)
        return block

    def emit_op(self, op):
        instr = Instruction(op, self.lineno)
        self.instrs.append(instr)
        if op == ops.RETURN_VALUE:
            self.current_block.have_return = True
        return instr

    def emit_op_arg(self, op, arg):
        self.instrs.append(Instruction(op, self.lineno, arg))

    def emit_op_name(self, op, container, name):
        self.emit_op_arg(op, self.add_name(container, name))

    def emit_jump(self, op, block_to, absolute=False):
        self.emit_op(op).jump_to(block_to, absolute)

    def add_name(self, container, name):
        name = self.scope.mangle(name)
        try:
            index = container[name]
        except KeyError:
            index = len(container)
            container[name] = index
        return index

    def add_const(self, obj):
        space = self.space
        w_key = space.newtuple([obj, space.type(obj)])
        w_len = space.finditem(self.w_consts, w_key)
        if w_len is None:
            w_len = space.len(self.w_consts)
            space.setitem(self.w_consts, w_key, w_len)
        return space.int_w(w_len)

    def load_const(self, obj):
        index = self.add_const(obj)
        self.emit_op_arg(ops.LOAD_CONST, index)

    def update_position(self, node):
        self.lineno = node.lineno
        if self.first_lineno == -1:
            self.first_lineno = node.lineno

    def _resolve_block_targets(self, blocks):
        last_extended_arg_count = 0
        while True:
            extended_arg_count = 0
            offset = 0
            for block in blocks:
                block.offset = offset
                offset += block.code_size()
            for block in blocks:
                offset = block.offset
                for instr in block.instructions:
                    offset += instr.size()
                    if instr.jump:
                        target, absolute = instr.jump
                        if absolute:
                            jump_arg = target.offset
                        else:
                            jump_arg = target.offset - offset
                        instr.arg = jump_arg
                        if jump_arg > 0xFFFF:
                            extended_arg_count += 1
            if extended_arg_count == last_extended_arg_count:
                break
            else:
                last_extended_arg_count = extended_arg_count

    def _build_consts_array(self):
        w_consts = self.w_consts
        space = self.space
        consts_w = [space.w_None] * space.int_w(space.len(w_consts))
        w_iter = space.iter(w_consts)
        first = space.wrap(0)
        while True:
            try:
                w_key = space.next(w_iter)
            except OperationError, e:
                if not e.match(space, space.w_StopIteration):
                    raise
                break
            w_index = space.getitem(w_consts, w_key)
            consts_w[space.int_w(w_index)] = space.getitem(w_key, first)
        return consts_w

    def _get_code_flags(self):
        raise NotImplementedError

    def _stacksize(self, blocks):
        for block in blocks:
            block.marked = False
            block.initial_depth = -1000
        return self._recursive_stack_depth_walk(blocks[0], 0, 0)

    def _recursive_stack_depth_walk(self, block, depth, max_depth):
        if block.marked or block.initial_depth >= depth:
            return max_depth
        block.marked = True
        block.initial_depth = depth
        for instr in block.instructions:
            depth += _opcode_stack_effect(instr.opcode, instr.arg)
            if depth >= max_depth:
                max_depth = depth
            if instr.jump:
                max_depth = self._recursive_stack_depth_walk(instr.jump[0],
                                                             depth, max_depth)
                if instr.opcode == ops.JUMP_ABSOLUTE or \
                        instr.opcode == ops.JUMP_FORWARD:
                    break
        if block.next_block:
            max_depth = self._recursive_stack_depth_walk(block.next_block,
                                                         depth, max_depth)
        block.marked = False
        return max_depth

    def _build_lnotab(self, blocks):
        lineno_table_builder = LinenoTableBuilder(self.first_lineno)
        for block in blocks:
            offset = block.offset
            for instr in block.instructions:
                lineno_table_builder.note_lineno_here(offset, instr.lineno)
                offset += instr.size()
        return lineno_table_builder.get_table()

    def assemble(self):
        if self.lineno == -1:
            self.lineno = self.first_lineno
        if not self.current_block.have_return:
            self.use_next_block()
            if self.add_none_to_final_return:
                self.load_const(self.space.w_None)
            self.emit_op(ops.RETURN_VALUE)
        blocks = self.first_block.post_order()
        self._resolve_block_targets(blocks)
        lnotab = self._build_lnotab(blocks)
        stack_depth = self._stacksize(blocks)
        consts_w = self._build_consts_array()
        names = _list_from_dict(self.names)
        var_names = _list_from_dict(self.var_names)
        cell_names = _list_from_dict(self.cell_vars)
        free_names = _list_from_dict(self.free_vars, len(cell_names))
        flags = self._get_code_flags() | self.compile_info.flags
        bytecode = ''.join([block.get_code() for block in blocks])
        return pycode.PyCode(self.space,
                             self.argcount,
                             len(self.var_names),
                             stack_depth,
                             flags,
                             bytecode,
                             consts_w,
                             names,
                             var_names,
                             self.compile_info.filename,
                             self.name,
                             self.first_lineno,
                             lnotab,
                             free_names,
                             cell_names)


def _list_from_dict(d, offset=0):
    result = [None] * len(d)
    for obj, index in d.iteritems():
        result[index - offset] = obj
    return result


_static_opcode_stack_effects = {
    ops.POP_TOP : -1,
    ops.ROT_TWO : 0,
    ops.ROT_THREE : 0,
    ops.ROT_FOUR : 0,
    ops.DUP_TOP : 1,

    ops.UNARY_POSITIVE : 0,
    ops.UNARY_NEGATIVE : 0,
    ops.UNARY_NOT : 0,
    ops.UNARY_CONVERT : 0,
    ops.UNARY_INVERT : 0,

    ops.LIST_APPEND : -1,

    ops.BINARY_POWER : -1,
    ops.BINARY_MULTIPLY : -1,
    ops.BINARY_DIVIDE : -1,
    ops.BINARY_MODULO : -1,
    ops.BINARY_ADD : -1,
    ops.BINARY_SUBTRACT : -1,
    ops.BINARY_SUBSCR : -1,
    ops.BINARY_FLOOR_DIVIDE : -1,
    ops.BINARY_TRUE_DIVIDE : -1,
    ops.BINARY_LSHIFT : -1,
    ops.BINARY_RSHIFT : -1,
    ops.BINARY_AND : -1,
    ops.BINARY_OR : -1,
    ops.BINARY_XOR : -1,

    ops.INPLACE_FLOOR_DIVIDE : -1,
    ops.INPLACE_TRUE_DIVIDE : -1,
    ops.INPLACE_ADD : -1,
    ops.INPLACE_SUBTRACT : -1,
    ops.INPLACE_MULTIPLY : -1,
    ops.INPLACE_DIVIDE : -1,
    ops.INPLACE_MODULO : -1,
    ops.INPLACE_POWER : -1,
    ops.INPLACE_LSHIFT : -1,
    ops.INPLACE_RSHIFT : -1,
    ops.INPLACE_AND : -1,
    ops.INPLACE_OR : -1,
    ops.INPLACE_XOR : -1,

    ops.SLICE+0 : 1,
    ops.SLICE+1 : 0,
    ops.SLICE+2 : 0,
    ops.SLICE+3 : -1,
    ops.STORE_SLICE+0 : -2,
    ops.STORE_SLICE+1 : -3,
    ops.STORE_SLICE+2 : -3,
    ops.STORE_SLICE+3 : -4,
    ops.DELETE_SLICE+0 : -1,
    ops.DELETE_SLICE+1 : -2,
    ops.DELETE_SLICE+2 : -2,
    ops.DELETE_SLICE+3 : -3,

    ops.STORE_SUBSCR : -2,
    ops.DELETE_SUBSCR : -2,

    ops.GET_ITER : 0,
    ops.FOR_ITER : 1,
    ops.BREAK_LOOP : 0,
    ops.CONTINUE_LOOP : 0,
    ops.SETUP_LOOP : 0,

    ops.PRINT_EXPR : -1,
    ops.PRINT_ITEM : -1,
    ops.PRINT_NEWLINE : 0,
    ops.PRINT_ITEM_TO : -2,
    ops.PRINT_NEWLINE_TO : -1,

    ops.WITH_CLEANUP : -1,
    ops.POP_BLOCK : 0,
    ops.END_FINALLY : -1,
    ops.SETUP_FINALLY : 3,
    ops.SETUP_EXCEPT : 3,

    ops.LOAD_LOCALS : 1,
    ops.RETURN_VALUE : -1,
    ops.EXEC_STMT : -3,
    ops.YIELD_VALUE : 0,
    ops.BUILD_CLASS : -2,
    ops.BUILD_MAP : 1,
    ops.COMPARE_OP : -1,

    ops.LOAD_NAME : 1,
    ops.STORE_NAME : -1,
    ops.DELETE_NAME : 0,

    ops.LOAD_FAST : 1,
    ops.STORE_FAST : -1,
    ops.DELETE_FAST : 0,

    ops.LOAD_ATTR : 0,
    ops.STORE_ATTR : -2,
    ops.DELETE_ATTR : -1,

    ops.LOAD_GLOBAL : 1,
    ops.STORE_GLOBAL : -1,
    ops.DELETE_GLOBAL : 0,

    ops.LOAD_CLOSURE : 1,
    ops.LOAD_DEREF : 1,
    ops.STORE_DEREF : -1,

    ops.LOAD_CONST : 1,

    ops.IMPORT_STAR : -1,
    ops.IMPORT_NAME : 0,
    ops.IMPORT_FROM : 1,

    ops.JUMP_FORWARD : 0,
    ops.JUMP_ABSOLUTE : 0,
    ops.JUMP_IF_TRUE : 0,
    ops.JUMP_IF_FALSE : 0,
}


def _compute_UNPACK_SEQUENCE(arg):
    return arg + 1

def _compute_DUP_TOPX(arg):
    return arg

def _compute_BUILD_TUPLE(arg):
    return 1 - arg

def _compute_BUILD_LIST(arg):
    return 1 - arg

def _compute_MAKE_CLOSURE(arg):
    return -arg

def _compute_MAKE_FUNCTION(arg):
    return -arg

def _compute_BUILD_SLICE(arg):
    if arg == 3:
        return -2
    else:
        return -1

def _compute_RAISE_VARARGS(arg):
    return -arg

def _num_args(oparg):
    return (oparg % 256) + 2 * (oparg / 256)

def _compute_CALL_FUNCTION(arg):
    return _num_args(arg)

def _compute_CALL_FUNCTION_VAR(arg):
    return _num_args(arg) - 1

def _compute_CALL_FUNCTION_KW(arg):
    return _num_args(arg) - 1

def _compute_CALL_FUNCTION_VAR_KW(arg):
    return _num_args(arg) - 2


_stack_effect_computers = {}
for name, func in globals().items():
    if name.startswith("_compute_"):
        _stack_effect_computers[getattr(ops, name[9:])] = func
for op, value in _static_opcode_stack_effects.iteritems():
    def func(arg, _value=value):
        return value
    _stack_effect_computers[op] = func
del name, func, op, value


def _opcode_stack_effect(op, arg):
    if we_are_translated():
        for possible_op in ops.unrolling_op_descs:
            if op == possible_op.index:
                return _stack_effect_computers[op](arg)
        else:
            raise AssertionError("unkown opcode: %s" % (op,))
    else:
        try:
            return _static_opcode_stack_effects[op]
        except KeyError:
            return _stack_effect_computers[op](arg)


class LinenoTableBuilder(object):

    def __init__(self, first_lineno):
        self.first = self.current_line = first_lineno
        self.current_off = 0
        self.table = []

    def get_table(self):
        return ''.join(self.table)

    def note_lineno_here(self, offset, lineno):
        # compute deltas
        line = lineno - self.current_line
        # Python assumes that lineno always increases with
        # increasing bytecode address (lnotab is unsigned char).
        # Depending on when SET_LINENO instructions are emitted
        # this is not always true.  Consider the code:
        #     a = (1,
        #          b)
        # In the bytecode stream, the assignment to "a" occurs
        # after the loading of "b".  This works with the C Python
        # compiler because it only generates a SET_LINENO instruction
        # for the assignment.
        if line >= 0:
            addr = offset - self.current_off
            if not addr and not line:
                return
            push = self.table.append
            while addr > 255:
                push(chr(255))
                push(chr(0))
                addr -= 255
            while line > 255:
                push(chr(addr))
                push(chr(255))
                line -= 255
                addr = 0
            if addr > 0 or line > 0:
                push(chr(addr))
                push(chr(line))
            self.current_line = lineno
            self.current_off = offset
