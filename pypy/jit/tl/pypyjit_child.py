from pypy.conftest import option
from pypy.rpython.lltypesystem import lltype
from pypy.jit.metainterp import warmspot
from pypy.module.pypyjit.portal import PyPyJitPolicy


def run_child(glob, loc):
    interp = loc['interp']
    graph = loc['graph']
    interp.malloc_check = False

    def returns_null(T, *args, **kwds):
        return lltype.nullptr(T)
    interp.heap.malloc_nonmovable = returns_null     # XXX

    print 'warmspot.jittify_and_run() started...'
    policy = PyPyJitPolicy(interp.typer.annotator.translator)
    option.view = True
    warmspot.jittify_and_run(interp, graph, [], policy=policy)
