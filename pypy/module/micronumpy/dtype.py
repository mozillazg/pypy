from pypy.interpreter.baseobjspace import ObjSpace, W_Root, Wrappable
from pypy.interpreter.error import OperationError
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.gateway import interp2app

def unwrap_int(space, w_x):
    return space.int_w(w_x)
def coerce_int(space, w_x):
    return unwrap_int(space, space.int(w_x))

def unwrap_float(space, w_x):
    return space.float_w(w_x)
def coerce_float(space, w_x):
    return unwrap_float(space, space.float(w_x))

from pypy.rlib.rarithmetic import r_singlefloat as float32

def unwrap_float32(space, w_x):
    return float32(space.float_w(w_x))
def coerce_float32(space, w_x):
    return unwrap_float32(space, space.float(w_x))

def create_factory(result_factory):
    def factory(t):
        return result_factory[t]
    return factory

class DynamicType(Wrappable):
    def __init__(self, code, name, applevel_type):
        self.code = code
        self.name = name
        self.applevel_type = applevel_type

    def descr_eq(self, space, w_x):
        if space.abstract_isinstance_w(w_x, space.w_type):
            return space.eq(self.applevel_type, w_x) #FIXME: correct comparison?
        else:
            try:
                code = space.str_w(w_x)
                if self.code == code:
                    return space.w_True
                elif self.name == code:
                    return space.w_True
                else:
                    raise OperationError(space.w_TypeError, space.wrap("data type not understood"))
            except OperationError, e:
                raise OperationError(space.w_TypeError, space.wrap("data type not understood"))
    descr_eq.unwrap_spec = ['self', ObjSpace, W_Root]
DynamicType.typedef = TypeDef('dtype',
                              __eq__ = interp2app(DynamicType.descr_eq),
                             )

class DynamicTypes(object):
    result_types = {
                    ('i', 'i'): 'i',
                    ('i', 'd'): 'd',
                    ('d', 'i'): 'd',
                    ('d', 'd'): 'd',
                   }

    def __init__(self):
        self.dtypes = {}

    def typecode(self, space, w_type):
        try:
            assert isinstance(w_type, DynamicType)
            return w_type.code
        except AssertionError, e: pass

        try:
            return space.str_w(w_type)
        except OperationError, e:
            typecode_mapping = {
                                space.w_int: 'i',
                                space.w_float: 'd',
                               }
            try:
                return typecode_mapping[w_type]
            except IndexError, e:
                raise OperationError(space.w_TypeError,
                        space.wrap("Can't understand type."))

    def result_mapping(self, space, types):
        types = (self.typecode(space, types[0]),
                 self.typecode(space, types[1]))
        return self.result_types[types]

    def iterable_type(self, space, w_xs):
        xs = space.fixedview(w_xs)
        result_type = 'i'
        for i in range(len(xs)):
            try:
                atype = self.iterable_type(space, xs[i])
            except OperationError, e:
                if not e.match(space, space.w_TypeError):
                    raise
                atype = self.typecode(space, space.type(xs[i]))
            result_type = self.result_types[(result_type, atype)]
        return result_type

    def verify_dtype_dict(self, space):
        if not self.dtypes:
            self.dtypes.update(
                               {
                                'i': DynamicType('i', 'int32', space.w_int),
                                'd': DynamicType('d', 'float64', space.w_float),
                               }
                              )

    def retrieve_dtype(self, space, t):
        self.verify_dtype_dict(space)
        return self.dtypes[t]

    def get_dtype(self, space, w_type):
        try:
            t = space.str_w(w_type)
        except OperationError, e:
            if e.match(space, space.w_TypeError):
                t = self.typecode(space, w_type)
            else:
                raise
        return self.retrieve_dtype(space, t)

    def sdarray(self, space, length, w_dtype):
        from pypy.module.micronumpy.sdarray import sdresult
        return sdresult(self.typecode(space, w_dtype))(space, length, w_dtype)

    def mdarray(self, space, shape, w_dtype):
        from pypy.module.micronumpy.mdarray import mdresult
        return mdresult(self.typecode(space, w_dtype))(space, shape, w_dtype)

dtypes = DynamicTypes()
iterable_type = dtypes.iterable_type
typecode = dtypes.typecode
result_mapping = dtypes.result_mapping
get_dtype = dtypes.get_dtype
retrieve_dtype = dtypes.retrieve_dtype
sdarray = dtypes.sdarray
mdarray = dtypes.mdarray
