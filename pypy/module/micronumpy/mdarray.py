from pypy.interpreter.error import OperationError
from pypy.interpreter.typedef import TypeDef, GetSetProperty
from pypy.interpreter.gateway import interp2app
from pypy.interpreter.baseobjspace import W_Root
from pypy.rlib.debug import make_sure_not_resized

from pypy.module.micronumpy.array import BaseNumArray
from pypy.module.micronumpy.array import base_typedef
from pypy.module.micronumpy.array import construct_array
from pypy.module.micronumpy.array import array as array_fromseq
from pypy.module.micronumpy.array import validate_index

from pypy.module.micronumpy.dtype import unwrap_int, coerce_int
from pypy.module.micronumpy.dtype import unwrap_float, coerce_float

def compute_pos(space, indexes, dim):
    current = 1
    pos = 0
    indexes.reverse()
    for i in range(len(indexes)):
        index = indexes[i]
        d = dim[i]
        if index >= d or index <= -d - 1:
            raise OperationError(space.w_IndexError,
                                 space.wrap("invalid index"))
        if index < 0:
            index = d + index
        pos += index * current
        current *= d
    return pos

def compute_slices(space, slices, dims):
    slices = space.fixedview(slices)
    if len(slices) > len(dims):
        raise OperationError(space.w_IndexError,
                             space.wrap('too many indices'))
    strides = []
    i = 1
    for dim in dims:
        strides.append(i)
        i *= dim
    shape = dims[:]
    strides.reverse()
    newshape = []
    extract = [0]
    slicelen = i #saved
    for i in range(len(slices)):
        w_index = slices[i]
        if space.is_true(space.isinstance(w_index, space.w_slice)):
            newextract = []
            l = shape[i]
            stride = strides[i]
            start, stop, step, slen = w_index.indices4(space, l)
            if slen == 0:
                extract = []
                continue #as in numpy
            newshape.append(slen)
            if step == 1:
                for i in range(len(extract)):
                    extract[i] += start*stride
                slicelen = stride*slen
            else:
                for i in range(len(extract)):
                    st = extract[i]
                    for j in range(slicelength):
                        newextract.append(st+start*stride)
                        start += step
                extract = newextract
                slicelen = stride
        elif space.is_w(w_index, space.w_Ellipsis):
            newshape.append(shape[i])
        else: #Must be integer
            try:
                index = space.int_w(w_index)
            except TypeError, e:
                raise OperationError(space.w_IndexError,
                                     space.wrap('Wrong index'))
            stride = strides[i]
            start = index*stride
            for i in range(len(extract)):
                extract[i] += start
            #No adding for shape
            slicelen = stride

        newshape.extend(shape[i+1:]) #add rest of shape
        #all slices are absolutely eqi-length
        return newshape, extract, slicelen


class BaseMultiDimArray(BaseNumArray): pass

def descr_dtype(space, self):
    return self.dtype

def descr_shape(space, self):
    return space.newtuple([space.wrap(dim) for dim in self.shape])

def create_mdarray(data_type, unwrap, coerce):
    class MultiDimArray(BaseMultiDimArray):
        def __init__(self, space, shape, w_dtype):
            self.shape = shape
            self.space = space
            self.dtype = w_dtype
            size = 1
            for dimension in shape:
                size *= dimension
            self.storage = [data_type(0.0)] * size
            make_sure_not_resized(self.storage)

        def load_iterable(self, w_xs):
            self._internal_load(w_xs, self.shape, [])

        def _internal_load(self, w_xs, shape, indexes):
            space = self.space
            length = shape[0]
            xs = space.fixedview(w_xs, length)
            shapemismatch = OperationError(space.w_ValueError,
                                           space.wrap('shape mismatch'))
            for i in range(length):
                try:
                    w_x = xs[i]
                except IndexError:
                    raise shapemismatch
                try:
                    space.iter(w_x)
                except OperationError, e:
                    if e.match(space, space.w_TypeError):
                        if len(shape)>1:
                            raise shapemismatch
                        else:
                            pos = compute_pos(space, indexes+[i], self.shape)
                            self.storage[pos]=coerce(space, w_x)
                    elif e.match(space, space.w_IndexError):
                        raise shapemismatch
                    else:
                        raise
                else:
                    self._internal_load(w_x, shape[1:], indexes+[i])

        def _unpack_indexes(self, space, w_index):
            indexes = [space.int_w(w_i) for w_i in space.fixedview(w_index)]
            if len(indexes) != len(self.shape):
                raise OperationError(space.w_IndexError,
                        space.wrap('shape mismatch'))
            return indexes

        def descr_getitem(self, w_index):
            space = self.space
            validate_index(self, space, w_index)
            try:
                space.iter(w_index)
            except OperationError, e:
                if not e.match(space, space.w_TypeError):
                    raise
                w_index = space.newlist([w_index])
            try:
                indexes = self._unpack_indexes(space, w_index)
            except OperationError, e:
                if not (e.match(space, space.w_IndexError) or
                        e.match(space, space.w_TypeError)):
                    raise
                shape, regions, l = compute_slices(space, w_index, self.shape)
                res = construct_array(space, shape, self.dtype)
                i = 0
                if len(regions) > 0:
                    for start in regions:
                        res.storage[i:i+l] = self.storage[start:start+l]
                        i += l
                return space.wrap(res)
            else:
                pos = compute_pos(space, indexes, self.shape)
                return space.wrap(self.storage[pos])
        descr_getitem.unwrap_spec = ['self', W_Root]

        def descr_setitem(self, w_index, w_value):
            space = self.space
            try:
                indexes = self._unpack_indexes(space, w_index)
            except OperationError, e:
                if not e.match(space, space.w_IndexError):
                    #not raised by _unpack_indexes
                    raise
                shape, regions, lslice = \
                                    compute_slices(space, w_index, self.shape)
                try:
                    space.iter(w_value)
                except OperationError, e:
                    if not e.match(space, space.w_TypeError):
                        raise
                    value = coerce(space, w_value)
                    for start in regions:
                        self.storage[start:start+lslice]=[value]*lslice
                    return
                arr = array_fromseq(space, w_value)
                ls = len(arr.shape)
                lss = len(self.shape)
                if not (ls <= lss and arr.shape == self.shape[lss-ls:lss]):
                    raise OperationError(space.w_ValueError,
                                         space.wrap('array dimensions '
                                         'are not compatible for copy'))
                                         #exactly as in numpy
                # /S\ - DO NOT EDIT if you're not sure!
                #we may exit earlier, but we are true purists and wonna check
                if len(regions) == 0: return
                l = len(arr.storage)
                if lslice > l: #long slice
                    iters = lslice//l
                    assert lslice == l*iters
                    for start in regions:
                        for i in range(iters):
                            self.storage[start:start+l] = arr.storage
                            start += l
                else:
                    i = 0
                    for start in regions:
                        self.storage[start:start+l] = arr.storage[i:i+lslice]
                        if i > l:
                            i = i-l
                #Looks like perfect
            else:
                pos = compute_pos(space, indexes, self.shape)
                self.storage[pos] = coerce(space, w_value)
        descr_setitem.unwrap_spec = ['self', W_Root, W_Root]

        def len(self):
            return self.shape[0]

        def descr_len(self):
            space = self.space
            return space.wrap(self.len())
        descr_len.unwrap_spec = ['self']

        def descr_str(self):
            return self.space.str(self.space.wrap(self.storage))
        descr_str.unwrap_spec = ['self']

    MultiDimArray.typedef = \
            TypeDef('ndarray', base_typedef,
                    __len__ = interp2app(MultiDimArray.descr_len),
                    __getitem__ = interp2app(MultiDimArray.descr_getitem),
                    __setitem__ = interp2app(MultiDimArray.descr_setitem),
                    __str__ = interp2app(MultiDimArray.descr_str),
                    dtype = GetSetProperty(descr_dtype, cls = MultiDimArray),
                    shape = GetSetProperty(descr_shape, cls = MultiDimArray),
                   )
    return MultiDimArray

MultiDimIntArray = create_mdarray(int, unwrap_int, coerce_int)
MultiDimFloatArray = create_mdarray(float, unwrap_float, coerce_float)

class ResultFactory(object):
    def __init__(self, space):
        self.space = space

        self.types = {
            space.w_int:   MultiDimIntArray,
            space.w_float: MultiDimFloatArray,
                     }

result_factory = None
def mdresult(space, t):
    global result_factory
    if result_factory is None:
        result_factory = ResultFactory(space)
    return result_factory.types[t]
