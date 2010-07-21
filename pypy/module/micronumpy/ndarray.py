from pypy.interpreter.baseobjspace import ObjSpace, W_Root, Wrappable
from pypy.interpreter.error import OperationError
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.gateway import interp2app, NoneNotWrapped
from pypy.interpreter.baseobjspace import ObjSpace, W_Root, Wrappable
from pypy.rlib.debug import make_sure_not_resized

def unpack_shape(space, w_shape):
    if space.is_true(space.isinstance(w_shape, space.w_int)):
        return [space.int_w(w_shape)]
    shape_w = space.fixedview(w_shape)
    return [space.int_w(w_i) for w_i in shape_w]

def infer_shape(space, w_values): 
    return [space.int_w(space.len(w_values))] #TODO: handle multi-dimensional arrays...

def validate_index(self, space, w_i):
    try:
        index_dimensionality = space.int_w(space.len(w_i))
        array_dimensionality = len(self.array.shape)
        if index_dimensionality > array_dimensionality:
            raise OperationError(space.w_IndexError,
                    space.wrap("Index dimensionality (%d) greater than array dimensionality (%d)." % (index_dimensionality, array_dimensionality)))
    except OperationError, e:
        if e.match(space, space.w_TypeError): pass
        else: raise


def descr_new(space, w_cls, w_shape,
              w_buffer=NoneNotWrapped, w_offset=NoneNotWrapped,
              w_strides=NoneNotWrapped, order=NoneNotWrapped):
    result = ndarray(space, w_None, w_shape, None)
    return space.wrap(result)
descr_new.unwrap_spec = [ObjSpace, W_Root, W_Root,
                         W_Root, W_Root, 
                         W_Root, str]
