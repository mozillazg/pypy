from pypy.tool.pairtype import extendabletype
from pypy.interpreter.astcompiler import ast

# Extra bytecode optimizations.  The visitor pattern is a bit of a mess
# for these, so we simply stick new methods on the nodes.

OPTIMIZE = True

def is_constant_false(space, node):
    return isinstance(node, ast.Const) and not space.is_true(node.value)

def is_constant_true(space, node):
    return isinstance(node, ast.Const) and space.is_true(node.value)


class __extend__(ast.Node):
    __metaclass__ = extendabletype

    def opt_accept_jump_if(self, codegen, condition, target):
        """Generate code equivalent to:
               self.accept()
               JUMP_IF_condition target
        except that the value left on the stack afterwards (both if the
        branch is taken or not) can be garbage.
        """
        self.accept(codegen)
        if condition:
            codegen.emitop_block('JUMP_IF_TRUE', target)
        else:
            codegen.emitop_block('JUMP_IF_FALSE', target)


if OPTIMIZE:

    class __extend__(ast.Not):
        __metaclass__ = extendabletype

        def opt_accept_jump_if(self, codegen, condition, target):
            self.expr.opt_accept_jump_if(codegen, not condition, target)


    class __extend__(ast.AbstractTest):
        __metaclass__ = extendabletype

        def _accept_jump_if_any_is(self, codegen, condition, target):
            # generate a "jump if any of the nodes' truth value is 'condition'"
            garbage_on_stack = False
            for node in self.nodes:
                if garbage_on_stack:
                    codegen.emit('POP_TOP')
                node.opt_accept_jump_if(codegen, condition, target)
                garbage_on_stack = True
            assert garbage_on_stack

        def opt_accept_jump_if(self, codegen, condition, target):
            if condition == self.is_and:
                # jump only if all the nodes' truth values are equal to
                # 'condition'
                end = codegen.newBlock()
                self._accept_jump_if_any_is(codegen, not condition, end)
                codegen.emitop_block('JUMP_FORWARD', target)
                codegen.nextBlock(end)
            else:
                self._accept_jump_if_any_is(codegen, condition, target)


    class __extend__(ast.And):
        __metaclass__ = extendabletype
        is_and = True

    class __extend__(ast.Or):
        __metaclass__ = extendabletype
        is_and = False
