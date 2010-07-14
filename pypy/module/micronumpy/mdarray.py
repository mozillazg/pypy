from pypy.interpreter.error import OperationError
from pypy.interpreter.typedef import TypeDef, GetSetProperty
from pypy.interpreter.gateway import interp2app
from pypy.interpreter.baseobjspace import W_Root, UnpackValueError
from pypy.objspace.std.sliceobject import W_SliceObject
from pypy.objspace.std.listobject import W_ListObject
from pypy.objspace.std.tupleobject import W_TupleObject
from pypy.rlib.debug import make_sure_not_resized

from pypy.module.micronumpy.array import BaseNumArray
from pypy.module.micronumpy.array import construct_array, infer_shape
from pypy.module.micronumpy.array import validate_index

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
    lenslices = len(slices)
    add = 0 # add to index
    for i in range(lenslices):
        factor = slicelen / strides[i-1] if i>0 else 1
        w_index = slices[i]
        i += add
        # somewhere here must be newaxis handling
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
                    newextract = make_sure_not_resized([0]*len(extract)*factor)
                    prestride = strides[i-1]
                    for j in range(len(extract)):
                        jf = j*factor
                        st = extract[j]
                        for k in range(factor):
                            newextract[jf+k] = st + start
                            st += prestride
                    extract = newextract
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
                    newextract = make_sure_not_resized([0]*len(extract)*factor*slen)
                    prestride = strides[i-1]
                    for j in range(len(extract)):
                        st = extract[j]
                        jfs = j*factor*slen
                        for f in range(factor):
                            fs = f*slen
                            index = start
                            for k in range(slen):
                                newextract[jfs+fs+k] = st + index*stride
                                index +=step
                            st += prestride
                    unoptimized = True
                extract = newextract
                slicelen = stride
        elif space.is_w(w_index, space.w_Ellipsis):
            howmuch = len(shape) - lenslices - add
            add += howmuch 
            newshape.extend(shape[i:i+howmuch+1])
            unoptimized = False
        elif space.is_w(w_index, space.w_None):
            newshape[len(newshape)-2:len(newshape)-1] = [1]
            add -= 1
        elif isinstance(w_index, W_ListObject): #newaxis -- an array contains
                                                #indices to extract
            #raise OperationError(space.w_NotImplementedError,
                    #space.wrap("newaxis are not implemented yet"))
            ixshape = infer_shape(space, w_index)
            axisarray = MultiDimIntArray(space, ixshape, 'i')
            axisarray.load_iterable(w_index) # let an exception propagate, if one
                                             # as in numpy
            newshape.extend(ixshape)
            indices = axisarray.storage
            nind = len(indices)
            del axisarray
            stride = strides[i]
            dim = shape[i]
            if not unoptimized:
                newextract = make_sure_not_resized([0] * len(extract) * factor)
                prestride = strides[i-1]
                for j in range(len(extract)):
                    ex = extract[j]
                    jf = j * factor
                    for k in range(factor):
                        newextract[jf + k] = ex
                        ex += prestride
            else:
                newextract = make_sure_not_resized(extract[:])

            extract = newextract
            newextract = make_sure_not_resized([0]* len(extract)*nind)
            for j in range(len(extract)):
                jn = j*nind
                for k in range(nind):
                    newextract[jn + k] = extract[j] + indices[k]*stride

            extract = newextract
            slicelen = stride

        else: #Must be integer
              #but we have checked.
            index = space.int_w(w_index)
            if not (-shape[i] <= index < shape[i]):
                raise OperationError(space.w_IndexError,
                                     space.wrap('index out of bounds'))
            if index < 0:
                index += shape[i]
            stride = strides[i]
            start = index*stride
            if unoptimized:
                for j in range(len(extract)):
                    extract[j] += start
            else:
                newextract = make_sure_not_resized([0] * len(extract) * factor)
                prestride = strides[i-1]
                for j in range(len(extract)):
                    jf = j * factor
                    st = extract[j]
                    for k in range(factor):
                        newextract[jf + k] = st + start
                        st += prestride
                extract = newextract
                unoptimized = True
            #No adding for shape
            slicelen = stride

    newshape.extend(shape[i+add+1:]) #add rest of shape
    #all slices are absolutely eqi-length
    return newshape, extract, slicelen


class BaseMultiDimArray(BaseNumArray): pass

def descr_dtype(space, self):
    return space.wrap(self.dtype)

def descr_shape(space, self):
    return space.newtuple([space.wrap(dim) for dim in self.shape])

def create_mdarray(data_type, unwrap, coerce):

    def create_math_operation(f):
        opname = f.__name__
        def common_math_operation(self, w_x, reversed):
            space = self.space
            inverse = False
            try:
                space.iter(w_x)
            except OperationError, e:
                if not e.match(space, space.w_TypeError):
                    raise
                result_t = result_mapping(space,
                                            (space.type(w_x), self.dtype))
                op2 = coerce(space, w_x)
                result = mdresult(result_t)(space, self.shape,
                                            retrieve_dtype(space, result_t))
                operation = result.__class__.client_scalar[opname]
            else:
                op2 = array_fromseq(space, w_x, None)
                if len(op2.shape) > len(self.shape):
                    self, op2 = op2, self
                    inverse = True
                lss = len(self.shape)
                ls = len(op2.shape)
                if not (list(op2.shape) == self.shape[lss-ls:lss] or
                        list(op2.shape) == self.shape[:ls]):
                    raise OperationError(space.w_ValueError,
                            space.wrap("shape mismatch: objects cannot be"
                                         " broadcast to the same shape"))
                result_t = result_mapping(space, (self.dtype, op2.dtype))
                result = mdresult(result_t)(space, self.shape,
                                            retrieve_dtype(space, result_t))
                operation = result.__class__.client_fixedview[opname]

            operation(result, self, op2, inverse^reversed)

            w_result = space.wrap(result)
            return w_result

        def math_operation(self, w_x):
            return common_math_operation(self, w_x, False)
        math_operation.unwrap_spec = ['self', W_Root]
        math_operation.__name__ = '%s_descr_%s'%(str(data_type), opname)

        def reversed_math_operation(self, w_x):
            return common_math_operation(self, w_x, True)
        reversed_math_operation.unwrap_spec = ['self', W_Root]
        reversed_math_operation.__name__ = '%s_descr_r%s'%(str(data_type), opname)

        return math_operation, reversed_math_operation

    def create_client_math_operation(f):
        def scalar_operation(self, source, x, inversed):
            for i in range(len(source.storage)):
                y = source.storage[i]
                self.storage[i] = data_type(f(x, y) if inversed else f(y, x))

        def fixedview_operation(self, source1, source2, inversed):
            #Here len(s1.storage)>=len(s2.storage)
            ls1 = len(source1.storage)
            ls2 = len(source2.storage)
            ll = len(source1.storage)//len(source2.storage)
            l2 = len(source2.storage)
            if list(source2.shape) == source1.shape[ls1 - ls2:ls1]:
                for i in range(ll):
                    il = i*l2
                    for j in range(l2):
                        idx = il + j
                        a = source1.storage[idx]
                        b = source2.storage[j]
                        self.storage[idx] = data_type(f(b, a) if inversed
                                                 else f(a, b))
            else:
                for i in range(l2):
                    il = i*ll
                    for j in range(ll):
                        idx = il + j
                        a = source1.storage[idx]
                        b = source2.storage[i]
                        self.storage[idx] = data_type(f(b, a) if inversed
                                                 else f(a, b))

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
                                            create_client_math_operation(mul)
        client_scalar['div'], client_fixedview['div'] = \
                                            create_client_math_operation(div)
        client_scalar['add'], client_fixedview['add'] = \
                                            create_client_math_operation(add)
        client_scalar['sub'], client_fixedview['sub'] = \
                                            create_client_math_operation(sub)
        descr_mul, descr_rmul = create_math_operation(mul)
        descr_div, descr_rdiv = create_math_operation(div)
        descr_add, descr_radd = create_math_operation(add)
        descr_sub, descr_rsub = create_math_operation(sub)

        def load_iterable(self, w_xs):
            self._internal_load(w_xs, self.shape, [])

        def _internal_load(self, w_xs, shape, indexes):
            space = self.space
            length = shape[0]
            shapemismatch = OperationError(space.w_ValueError,
                                           space.wrap('setting an array element'
                                                      'with a sequence'))
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

            try:
                field_name = space.str_w(w_index)
                raise OperationError(space.w_ValueError, #FIXME: if we were honest this would be NotImplemented
                                     space.wrap("field name %s not found" % field_name))
            except OperationError, e:
                if not e.match(space, space.w_TypeError):
                    raise
            if not isinstance(w_index, W_TupleObject):
                w_index = space.newtuple([w_index])
            validate_index(self, space, w_index)
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
            if not isinstance(w_index, W_TupleObject):
                w_index = space.newtuple([w_index])
            validate_index(self, space, w_index)
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
                        self.storage[start:start + lslice] = [value] * lslice
                    return
                arr = array_fromseq(space, w_value, None)
                larr = len(arr.storage)
                ls = len(arr.shape)
                lss = len(shape)
                noncompat = OperationError(space.w_ValueError, #FIXME: throws when it shouldn't
                                     space.wrap('array dimensions '
                                     'are not compatible for copy'))
                if ls > lss:
                    raise noncompat
                if list(arr.shape) == shape[lss-ls:lss]:
                    if len(regions) == 0: return
                    i = 0
                    if lslice > larr:
                        for start in regions:
                            for j in range(0, lslice, larr):
                                self.storage[start:start + larr] = arr.storage[:]
                                start += larr
                    else:
                        for start in regions:
                            self.storage[start:start + lslice] =\
                                    arr.storage[i:i + lslice]
                            i += lslice
                            if i > larr:
                                i -= larr
                elif list(arr.shape) == shape[:ls]:
                    if len(regions) == 0: return
                    if len(regions) < larr:
                        factor = larr // len(regions)
                        slen = lslice // factor
                        for j in range(len(regions)):
                            start = regions[j]
                            jf = j*factor
                            for k in range(factor):
                                self.storage[start:start + slen] = \
                                        make_sure_not_resized(
                                                [arr.storage[jf + k]] * slen)
                                start += slen
                    else:
                        i = 0
                        for item in arr.storage:
                            for start in regions[i:i+larr]:
                                self.storage[start:start + lslice] = [item] * lslice
                            i += larr
                else:
                    raise noncompat
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
            TypeDef('mdarray', #XXX: condemned
                    __len__ = interp2app(MultiDimArray.descr_len),
                    __getitem__ = interp2app(MultiDimArray.descr_getitem),
                    __setitem__ = interp2app(MultiDimArray.descr_setitem),

                    __add__ = interp2app(MultiDimArray.descr_add),
                    __sub__ = interp2app(MultiDimArray.descr_sub),
                    __mul__ = interp2app(MultiDimArray.descr_mul),
                    __div__ = interp2app(MultiDimArray.descr_div),

                    __radd__ = interp2app(MultiDimArray.descr_radd),
                    __rsub__ = interp2app(MultiDimArray.descr_rsub),
                    __rmul__ = interp2app(MultiDimArray.descr_rmul),
                    __rdiv__ = interp2app(MultiDimArray.descr_rdiv),

                    __str__ = interp2app(MultiDimArray.descr_str),

                    dtype = GetSetProperty(descr_dtype, cls = MultiDimArray),
                    shape = GetSetProperty(descr_shape, cls = MultiDimArray),
                   )
    return MultiDimArray
