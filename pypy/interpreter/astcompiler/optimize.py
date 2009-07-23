from pypy.interpreter.astcompiler import ast2 as ast
from pypy.tool import stdlib_opcode as ops


CONST_NOT_CONST = -1
CONST_FALSE = 0
CONST_TRUE = 1


class __extend__(ast.expr):

    def as_constant_truth(self, space):
        const = self.as_constant()
        if const is None:
            return CONST_NOT_CONST
        return int(space.is_true(const))

    def as_constant(self):
        return None

    def accept_jump_if(self, gen, condition, target):
        self.walkabout(gen)
        if condition:
            gen.emit_jump(ops.JUMP_IF_TRUE, target)
        else:
            gen.emit_jump(ops.JUMP_IF_FALSE, target)


class __extend__(ast.Num):

    def as_constant(self):
        return self.n


class __extend__(ast.Str):

    def as_constant(self):
        return self.s


class __extend__(ast.UnaryOp):

    def accept_jump_if(self, gen, condition, target):
        if self.op == ast.Not:
            self.operand.accept_jump_if(gen, not condition, target)
        else:
            ast.expr.accept_jump_if(self, gen, condition, target)



class __extend__(ast.BoolOp):

    def _accept_jump_if_any_is(self, gen, condition, target):
        self.values[0].accept_jump_if(gen, condition, target)
        for i in range(1, len(self.values)):
            gen.emit_op(ops.POP_TOP)
            self.values[i].accept_jump_if(gen, condition, target)

    def accept_jump_if(self, gen, condition, target):
        if condition and self.op == ast.And or \
                (not condition and self.op == ast.Or):
            end = gen.new_block()
            self._accept_jump_if_any_is(gen, not condition, end)
            gen.emit_jump(ops.JUMP_FORWARD, target)
            gen.use_next_block(end)
        else:
            self._accept_jump_if_any_is(gen, condition, target)
