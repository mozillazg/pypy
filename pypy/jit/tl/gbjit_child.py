from pypy.conftest import option
from pypy.rpython.lltypesystem import lltype
from pypy.jit.metainterp import warmspot
from pypy.jit.metainterp.policy import ManualJitPolicy

from pypy.translator.backendopt.support import find_calls_from

class GbJitPolicy(ManualJitPolicy):
    def look_inside_function(self, func):
        if "update_clock" in func.func_name:
            return False
        if "ll_int2hex" in func.func_name:
            return False
        return True # XXX for now

def run_child(glob, loc):
    import sys, pdb
    interp = loc['interp']
    graph = loc['graph']
    interp.malloc_check = False

    #def returns_null(T, *args, **kwds):
    #    return lltype.nullptr(T)
    #interp.heap.malloc_nonmovable = returns_null     # XXX

    print 'warmspot.jittify_and_run() started...'
    policy = GbJitPolicy(interp.typer.annotator.translator)
    option.view = True
    warmspot.jittify_and_run(interp, graph, [], policy=policy,
                             listops=True)
