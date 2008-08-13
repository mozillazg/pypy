from pypy.jit.codegen import model
# Wrapper Classes

class Register64(model.GenVar):
    def __init__(self, reg):
        self.reg = reg

# TODO: support 64-bit Constants
class Constant32(model.GenConst):
    def __init__(self, value):
        self.value = value