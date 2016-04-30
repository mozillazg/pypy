import pypy.module.micronumpy.constants as NPY
from pypy.interpreter.error import OperationError, oefmt
from pypy.interpreter.gateway import interp2app
from pypy.interpreter.typedef import TypeDef, GetSetProperty
from pypy.module.micronumpy import support
from pypy.module.micronumpy.base import convert_to_array, W_NumpyObject
from pypy.module.micronumpy.flatiter import W_FlatIterator
from rpython.rlib import jit
from strides import shape_agreement_multiple

def descr_new_broadcast(space, w_subtype, __args__):
    return W_Broadcast(space, __args__.arguments_w)

class W_Broadcast(W_NumpyObject):
    """
    Implementation of numpy.broadcast.
    This class is a simplified version of nditer.W_NDIter with fixed iteration for broadcasted arrays.
    """

    def __init__(self, space, args):
        num_args = len(args)
        if not (2 <= num_args <= NPY.MAXARGS):
            raise oefmt(space.w_ValueError,
                                 "Need at least two and fewer than (%d) array objects.", NPY.MAXARGS)

        self.seq = [convert_to_array(space, w_elem)
                    for w_elem in args]

        self.shape = shape_agreement_multiple(space, self.seq, shape=None)
        self.order = NPY.CORDER

        self.list_iter_state = []
        self.index = 0

        try:
            self.size = support.product_check(self.shape)
        except OverflowError as e:
            raise oefmt(space.w_ValueError, "broadcast dimensions too large.")

        self.list_iter_state = [W_FlatIterator(arr, self.shape, arr.get_order() != self.order)
                                for arr in self.seq]

        self.done = False

    def get_shape(self):
        return self.shape

    def get_order(self):
        return self.order

    def get_dtype(self):
        return self.seq[0].get_dtype() #XXX Fixme

    def get_size(self):
        return 0  #XXX Fixme

    def create_iter(self, shape=None, backward_broadcast=False):
        return self, self.list_iter_state # XXX Fixme

    def descr_iter(self, space):
        return space.wrap(self)

    def descr_get_shape(self, space):
        return space.newtuple([space.wrap(i) for i in self.shape])

    def descr_get_size(self, space):
        return space.wrap(self.size)

    def descr_get_index(self, space):
        return space.wrap(self.index)

    def descr_get_numiter(self, space):
        return space.wrap(len(self.list_iter_state))

    def descr_get_number_of_dimensions(self, space):
        return space.wrap(len(self.shape))

    def descr_get_iters(self, space):
        return space.newtuple(self.list_iter_state)

    @jit.unroll_safe
    def descr_next(self, space):
        if self.index >= self.size:
            self.done = True
            raise OperationError(space.w_StopIteration, space.w_None)
        self.index += 1
        res = [space.call_method(it, 'next') for it in self.list_iter_state]

        if len(res) < 2:
            return res[0]
        return space.newtuple(res)

    def descr_reset(self, space):
        self.index = 0
        self.done = False
        for it in self.list_iter_state:
            it.reset()

W_Broadcast.typedef = TypeDef("numpy.broadcast",
                              __new__=interp2app(descr_new_broadcast),
                              __iter__=interp2app(W_Broadcast.descr_iter),
                              next=interp2app(W_Broadcast.descr_next),
                              shape=GetSetProperty(W_Broadcast.descr_get_shape),
                              size=GetSetProperty(W_Broadcast.descr_get_size),
                              index=GetSetProperty(W_Broadcast.descr_get_index),
                              numiter=GetSetProperty(W_Broadcast.descr_get_numiter),
                              nd=GetSetProperty(W_Broadcast.descr_get_number_of_dimensions),
                              iters=GetSetProperty(W_Broadcast.descr_get_iters),
                              reset=interp2app(W_Broadcast.descr_reset),
                              )
