from pypy.interpreter.astcompiler import ast2 as ast
from pypy.interpreter.error import OperationError


class __extend__(ast.expr):

    constant = False

    def as_node_list(self, space):
        return None


class __extend__(ast.List):

    def as_node_list(self, space):
        return self.elts


class __extend__(ast.Tuple):

    def as_node_list(self, space):
        return self.elts


class __extend__(ast.Const):

    constant = True

    def as_node_list(self, space):
        try:
            values_w = space.unpackiterable(self.value)
        except OperationError:
            return None
        line = self.lineno
        column = self.col_offset
        return [ast.Const(w_obj, line, column) for w_obj in values_w]


class __extend__(ast.Str):

    constant = True


class __extend__(ast.Num):

    constant = True
