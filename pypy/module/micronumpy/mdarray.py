from pypy.interpreter.error import OperationError
from pypy.interpreter.typedef import TypeDef, GetSetProperty
from pypy.interpreter.gateway import interp2app
from pypy.interpreter.baseobjspace import W_Root, UnpackValueError
from pypy.objspace.std.sliceobject import W_SliceObject
from pypy.rlib.debug import make_sure_not_resized

from pypy.module.micronumpy.array import BaseNumArray
from pypy.module.micronumpy.array import base_typedef
from pypy.module.micronumpy.array import construct_array
from pypy.module.micronumpy.array import array as array_fromseq
from pypy.module.micronumpy.array import validate_index
from pypy.module.micronumpy.array import \
        mul_operation, div_operation, add_operation, sub_operation

from pypy.module.micronumpy.dtype import unwrap_int, coerce_int
from pypy.module.micronumpy.dtype import unwrap_float, coerce_float
from pypy.module.micronumpy.dtype import create_factory

def compute_pos(space, indexes, dim):
    current = 1
    pos = 0
    for i in range(len(indexes)-1, -1, -1):
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
    strides = make_sure_not_resized([0]*len(dims))
    stride = 1
    for i in range(len(dims)-1, -1, -1):
        strides[i] = stride
        stride *= dims[i]
    shape = dims[:]
    newshape = []
    extract = [0]
    slicelen = stride #saved
    unoptimized = True
    for i in range(len(slices)):
        factor = slicelen / strides[i-1] if i>0 else 1
        w_index = slices[i]
        if isinstance(w_index, W_SliceObject):
            l = shape[i]
            stride = strides[i]
            start, stop, step, slen = w_index.indices4(space, l)
            if slen == 0:
                extract = []
                newshape.append(0)
                continue #as in numpy
            newshape.append(slen)
            # I suspect that fiendish difficulty while will understand this code.
            # Please, understand before to edit.
            if step == 1:
                start *= stride
                if unoptimized:
                    for j in range(len(extract)):
                        extract[j] += start
                    unoptimized = False
                else:
                    TESTME
                slicelen = stride*slen
            else:
                if unoptimized:
                    newextract = make_sure_not_resized([0]*len(extract)*slen)
                    for j in range(len(extract)):
                        js = j*slen
                        st = extract[j]
                        index = start
                        for k in range(slen):
                            newextract[js + k] = st + index*stride
                            index += step
                else:
                    TESTME
                extract = newextract
                slicelen = stride
        elif space.is_w(w_index, space.w_Ellipsis):
            newshape.append(shape[i])
            unoptimized = False
        else: #Must be integer
            try:
                index = space.int_w(w_index)
            except TypeError, e:
                raise OperationError(space.w_IndexError,
                                     space.wrap('Wrong index'))
            if not (-shape[i] <= index < shape[i]):
                raise OperationError(space.w_IndexError,
                                     space.wrap('index out of range'))
            if index < 0:
                index += shape[i]
            stride = strides[i]
            start = index*stride
            if unoptimized:
                for j in range(len(extract)):
                    extract[j] += start
            else:
                newextract = make_sure_not_resized([0]*len(extract)*factor)
                prestride = strides[i-1]
                for j in range(len(extract)):
                    jf = j*factor
                    st = extract[j]
                    for k in range(factor):
                        newextract[jf+k] = st + start
                        st += prestride
                extract = newextract
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

MUL = mul_operation()
DIV = div_operation()
ADD = add_operation()
SUB = sub_operation()

def create_mdarray(data_type, unwrap, coerce):

    def create_math_operation(f):
        opname = f.__name__
        def math_operation(self, w_x):
            space = self.space
            try:
                space.iter(w_x)
            except OperationError, e:
                if not e.match(space, space.w_TypeError):
                    raise
                result_t = result_mapping(space,
                                            (space.type(w_x), self.dtype))
                op2 = coerce(space, w_x)
                result = sdresult(space, result_t)(
                                                space, self.len(), result_t
                                                )
                operation = result.__class__.client_scalar[opname]
            else:
                op2 = array_fromseq(space, w_x)
                if len(op2.shape) > len(self.shape):
                    self, op2 = op2, self
                lss = len(self.shape)
                ls = len(op2.shape)
                if not op2.shape == self.shape[lss-ls:lss]:
                    raise OperationError(space.w_ValueError,
                            space.wrap("shape mismatch: objects cannot be"
                                         " broadcast to the same shape"))
                result_t = result_mapping(space, (self.dtype, op2.dtype))
                result = mdresult(space, result_t)(space, self.shape, result_t)
                operation = result.__class__.client_fixedview[opname]

            operation(result, self, op2)

            w_result = space.wrap(result)
            return w_result
        math_operation.unwrap_spec = ['self', W_Root]
        math_operation.__name__ = 'descr_'+opname
        return math_operation

    def create_client_math_operation(f):
        def scalar_operation(self, source, x):
            for i in range(len(source.storage)):
                self.storage[i] = data_type(f(source.storage[i], x))

        def fixedview_operation(self, source1, source2):
            #Here len(s1.storage)>=len(s2.storage)
            ll = len(source1.storage)//len(source2.storage)
            l2 = len(source2.storage)
            for i in range(ll):
                for j in range(l2):
                    idx=i*l2+j
                    self.storage[idx] = data_type(f(source1.storage[idx],
                                                    source2.storage[j]))

        return scalar_operation, fixedview_operation

    class MultiDimArray(BaseMultiDimArray):
        def __init__(self, space, shape, w_dtype):
            self.shape = make_sure_not_resized(shape)
            self.space = space
            self.dtype = w_dtype
            size = 1
            for dimension in shape:
                size *= dimension
            self.storage = make_sure_not_resized([data_type(0.0)] * size)

        client_scalar = {}
        client_fixedview = {}

        client_scalar['mul'], client_fixedview['mul'] = \
                                            create_client_math_operation(MUL)
        client_scalar['div'], client_fixedview['div'] = \
                                            create_client_math_operation(DIV)
        client_scalar['add'], client_fixedview['add'] = \
                                            create_client_math_operation(ADD)
        client_scalar['sub'], client_fixedview['sub'] = \
                                            create_client_math_operation(SUB)
        descr_mul = create_math_operation(MUL)
        descr_div = create_math_operation(DIV)
        descr_add = create_math_operation(ADD)
        descr_sub = create_math_operation(SUB)


        def load_iterable(self, w_xs):
            self._internal_load(w_xs, self.shape, [])

        def _internal_load(self, w_xs, shape, indexes):
            space = self.space
            length = shape[0]
            shapemismatch = OperationError(space.w_ValueError,
                                           space.wrap('shape mismatch'))
            try:
                xs = space.fixedview(w_xs, length)
            except UnpackValueError:
                raise shapemismatch
            for i in range(length):
                w_x = xs[i]
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
            validate_index(self, space, w_index)
            try:
                space.iter(w_index)
            except OperationError, e:
                if not (e.match(space, space.w_IndexError) or
                        e.match(space, space.w_TypeError)):
                    raise
                w_index = space.newlist([w_index])
            try:
                indexes = self._unpack_indexes(space, w_index)
            except OperationError, e:
                if not (e.match(space, space.w_IndexError) or
                        e.match(space, space.w_TypeError)):
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
                arr = array_fromseq(space, w_value, None)
                ls = len(arr.shape)
                lss = len(shape)
                if not (ls <= lss and list(arr.shape) == shape[lss-ls:lss]):
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

mdresult = create_factory({'i': MultiDimIntArray, 'd': MultiDimFloatArray})
