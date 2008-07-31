from pypy.jit.codegen import model


class IntVar(model.GenVar):
    def __init__(self, reg):
        self.reg = reg

class Const(model.GenConst):
    def __init__(self, value):
        self.value = value