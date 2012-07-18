
from pypy.objspace.std.embedding import prepare_function, Cache, call_function
from pypy.rpython.lltypesystem import rffi, lltype
from pypy.interpreter.function import Function

class TestEmbedding(object):
    def test_prepare_function(self):
        space = self.space
        TP = rffi.CArray(rffi.CCHARP)
        ll_arr = lltype.malloc(TP, 2, flavor='raw')
        ll_arr[0] = rffi.str2charp("f")
        ll_arr[1] = rffi.str2charp("g")
        ll_source = rffi.str2charp('''
def f(a, b):
    return a + b
def g(a):
    return a - 2
''')
        prepare_function(space, ll_arr, ll_source)
        w_f = space.getitem(space.fromcache(Cache).w_globals, space.wrap('f'))
        assert isinstance(w_f, Function)
        w_res = space.call_function(w_f, space.wrap(1), space.wrap(2))
        assert space.int_w(w_res) == 3
        ll_args = lltype.malloc(rffi.CArray(lltype.Signed), 2, flavor='raw')
        ll_args[0] = 1
        ll_args[1] = 2
        call_function(space, ll_arr[0], 2, ll_args)
        lltype.free(ll_arr[0], flavor='raw')
        lltype.free(ll_arr[1], flavor='raw')
        lltype.free(ll_arr, flavor='raw')
        lltype.free(ll_source, flavor='raw')
        lltype.free(ll_args, flavor='raw')
