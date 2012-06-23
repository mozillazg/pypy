
from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.typedef import TypeDef

class W_NDArray(Wrappable):
    def __init__(self, impl):
        self.impl = impl

class BaseArrayImpl(object):
    pass

class Scalar(BaseArrayImpl):
    pass

class ConcreteArray(BaseArrayImpl):
    def __init__(self, shape):
        self.shape = shape

W_NDArray.typedef = TypeDef('ndarray',
    __module__ = 'numpypy',
)
