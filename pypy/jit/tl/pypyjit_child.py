from pypy.rpython.lltypesystem import lltype
from pypy.jit.metainterp import warmspot


def run_child(glob, loc):
    interp = loc['interp']
    graph = loc['graph']
    interp.malloc_check = False

    def returns_null(T, *args, **kwds):
        return lltype.nullptr(T)
    interp.heap.malloc_nonmovable = returns_null     # XXX

    print 'warmspot.jittify_and_run() started...'
    warmspot.jittify_and_run(interp, graph, [])
