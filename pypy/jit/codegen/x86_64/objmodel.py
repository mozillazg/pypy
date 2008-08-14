from pypy.jit.codegen import model
# Wrapper Classes

class Register64(model.GenVar):
    _dispatchname = "_QWREG"
    def __init__(self, reg):
        self.reg = reg

# TODO: support 64-bit Constants
class Constant32(model.GenConst):
    _dispatchname = "_IMM32"
    def __init__(self, value):
        self.value = value
