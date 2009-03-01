
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.rlib.objectmodel import we_are_translated
from pypy.translator.c.test.test_genc import compile
import ctypes

GC_MALLOC = lltype.Ptr(lltype.FuncType([lltype.Signed], llmemory.Address))

def gc_malloc(size):
    return llop.call_boehm_gc_alloc(llmemory.Address, size)

def gc_malloc_fnaddr():
    """Returns the address of the Boehm 'malloc' function."""
    if we_are_translated():
        gc_malloc_ptr = llhelper(GC_MALLOC, gc_malloc)
        return lltype.cast_ptr_to_int(gc_malloc_ptr)
    else:
        try:
            from ctypes import cast, c_void_p, util
            path = util.find_library('gc')
            if path is None:
                raise ImportError("Boehm (libgc) not found")
            boehmlib = ctypes.cdll.LoadLibrary(path)
        except ImportError, e:
            import py
            py.test.skip(str(e))
        else:
            GC_malloc = boehmlib.GC_malloc
            return cast(GC_malloc, c_void_p).value

def c_meta_interp(function, args, **kwds):
    from pypy.translator.translator import TranslationContext
    from pypy.jit.metainterp.warmspot import WarmRunnerDesc
    from pypy.jit.backend.x86.runner import CPU386
    
    t = TranslationContext()
    t.config.translation.gc = 'boehm'
    t.buildannotator().build_types(function, [int] * len(args))
    t.buildrtyper().specialize()
    warmrunnerdesc = WarmRunnerDesc(t, translate_support_code=True,
                                    CPUClass=CPU386,
                                    **kwds)
    warmrunnerdesc.state.set_param_threshold(3)          # for tests
    warmrunnerdesc.state.set_param_trace_eagerness(2)    # for tests
    warmrunnerdesc.finish()

