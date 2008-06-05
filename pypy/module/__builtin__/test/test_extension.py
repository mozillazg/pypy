from pypy.objspace.std.objspace import StdObjSpace, W_Object
from pypy.annotation.policy import AnnotatorPolicy
from pypy.annotation.binaryop import BINARY_OPERATIONS
from pypy.rpython.lltypesystem import lltype, rffi, ll2ctypes
from pypy.rlib.unroll import unrolling_iterable
from pypy.rlib.nonconst import NonConstant

# XXX Most of this module is an assembly of various hacks

# XXX Many space operations are missing

# XXX Need a way to check that both sides actually compiled the same
#     PyPyApi structure (e.g. a magic number)

class PyPyObjectType(lltype.OpaqueType):
    """An opaque object representing a Python object.
    When interpreted, it wraps a PyObject* containing a W_Object.
    When translated, it wraps a pointer to the translated W_Object structure.
    It plays the same role as the PyObject* in the CPython API.
    """
    _gckind = 'raw'
    __name__ = 'PyPyObject'
    def __init__(self):
        lltype.OpaqueType.__init__(self, 'PyPyObject')
        self.hints['external'] = 'C'
        self.hints['c_name'] = 'struct PyPyObject'
        self.hints['getsize'] = lambda: 4
    def __str__(self):
        return "PyPyObject"

PyPyObject = lltype.Ptr(PyPyObjectType())

BINARY_OP_TP = rffi.CCallback([PyPyObject, PyPyObject], PyPyObject)
UNARY_OP_TP = rffi.CCallback([PyPyObject], PyPyObject)
NEWINT_TP = rffi.CCallback([rffi.LONG], PyPyObject)
IS_TRUE_TP = rffi.CCallback([PyPyObject], lltype.Bool)

# definition of the PyPy API.
# XXX should use the ObjSpace.MethodTable
API_FIELDS = [(op, BINARY_OP_TP) for op in BINARY_OPERATIONS if '_' not in op]

# some of the ObjSpace.IrregularOpTable items
API_FIELDS.append(('newint', NEWINT_TP))
API_FIELDS.append(('getattr', UNARY_OP_TP))
API_FIELDS.append(('is_true', IS_TRUE_TP))

PyPyApiStruct = lltype.Struct('pypy_api', *API_FIELDS)

class ExtensionObjSpace(StdObjSpace):
    """This is the object space seen when external functions are annotated.
    most space operations are directed to one member of the API structure.
    """
    def __init__(self, apiptr):
        StdObjSpace.__init__(self)
        self.apiptr = apiptr

    def initialize(self):
        StdObjSpace.initialize(self)

        for name, _ in API_FIELDS:
            def wrapperFunc(name):
                def f(*args):
                    return getattr(self.apiptr[0], name)(*args)
                return f

            setattr(self, name, wrapperFunc(name))

class ExtensionAnnotatorPolicy(AnnotatorPolicy):
    allow_someobjects = False

    def specialize__wrap(pol,  funcdesc, args_s):
        # Do not create frozen wrapped constant
        typ = args_s[1].knowntype
        return funcdesc.cachedgraph(typ)

# The API structure is initialized in the main interpreter, with
# functions based on the standard ObjSpace.
# The fonctions pointers are then passed to the extension module,
# which may use them.

# All the API is serialized into a single string: a commma-separated
# list of numbers, representing the functions pointers :-)
def serializeAPI(space):
    import ctypes

    # XXX Could not find better
    keepalives = []
    def objectToNumber(object):
        keepalives.append(object)
        return id(object)
    def numberToObject(number):
        return ctypes.cast(number, ctypes.py_object).value

    callbacks = []
    for name, FNTYPE in API_FIELDS:
        def makefunc(name=name, FNTYPE=FNTYPE):
            # Build a C callback into the main object space.
            # The hard part is to convert a pypy.objspace.std.objspace.W_Object
            # (a CPython pointer), into a PyPyObject (a lltype pointer)
            def func(*args):
                newargs = []
                for arg, ARG in zip(args, FNTYPE.TO.ARGS):
                    if ARG is PyPyObject:
                        arg = numberToObject(arg._obj._storage)
                    newargs.append(arg)

                cres = getattr(space, name)(*newargs)

                if FNTYPE.TO.RESULT is PyPyObject:
                    assert isinstance(cres, W_Object)
                    return rffi.cast(PyPyObject, objectToNumber(cres))
                else:
                    return cres
            llfunc = rffi.llhelper(FNTYPE, func)
            return ll2ctypes.lltype2ctypes(llfunc)
        callbacks.append(makefunc())

    addresses = ",".join(str(ctypes.cast(c, ctypes.c_void_p).value)
                         for c in callbacks)

    return addresses

api_field_names = unrolling_iterable(enumerate(API_FIELDS))
def unserializeAPI(addresses):
    """This function is translated into the extension library.
    it takes a list of numbers, considers they are function pointers,
    and uses them to allocate a PyPyApi structure.
    """
    apimembers = addresses.split(",")
    api = lltype.malloc(PyPyApiStruct, flavor='raw')
    for i, (name, FNTYPE) in api_field_names:
        address = int(apimembers[i])
        funcptr = lltype.cast_int_to_ptr(FNTYPE, address)
        setattr(api, name, funcptr)
    return api

def compile(apiptr, func):
    stdobjspace = StdObjSpace()
    stdobjspace.initialize()

    addresses = serializeAPI(stdobjspace)

    def exportedfunc(addresses):
        api = unserializeAPI(addresses)
        apiptr[0] = api
        func()

    from pypy.translator.interactive import Translation
    t = Translation(exportedfunc, [str], policy=ExtensionAnnotatorPolicy())
    t.annotate()
    t.rtype()
    f = t.compile_c()

    def returnedfunc():
        f(addresses)

    return returnedfunc


# Now the interesting part
def test_extension_function():
    apiptr = lltype.malloc(lltype.Array(lltype.Ptr(PyPyApiStruct)),
                           1, immortal=True)

    space = ExtensionObjSpace(apiptr)

    def func():
        # (42 * 2) + 5 == 89
        w_x = space.wrap(42)
        w_y = space.mul(w_x, space.wrap(2))
        w_res = space.add(w_y, space.wrap(5))

        if space.is_true(space.eq(w_res, space.wrap(89))):
            print "OK!"

        # Negative test, to be sure that space.is_true does not return garbage.
        if space.is_true(space.eq(w_res, space.wrap(85))):
            print "KO!"

    f = compile(apiptr, func)

    f() # XXX catch stdout and check the presence of the "OK!" string
