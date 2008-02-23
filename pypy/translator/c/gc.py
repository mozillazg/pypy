import sys
from pypy.translator.c.support import cdecl
from pypy.translator.c.node import ContainerNode
from pypy.rpython.lltypesystem.lltype import \
     typeOf, Ptr, ContainerType, top_container
from pypy.rpython.memory.gctransform import \
     refcounting, boehm, framework, stacklessframework, llvmgcroot, asmgcroot
from pypy.rpython.lltypesystem import lltype, llmemory

class BasicGcPolicy(object):
    requires_stackless = False
    
    def __init__(self, db, thread_enabled=False):
        self.db = db
        self.thread_enabled = thread_enabled

    def common_gcheader_definition(self, defnode):
        if defnode.db.gctransformer is not None:
            HDR = defnode.db.gctransformer.gcheaderbuilder.HDR
            return [(name, HDR._flds[name]) for name in HDR._names]
        else:
            return []

    def common_gcheader_initdata(self, defnode):
        if defnode.db.gctransformer is not None:
            gct = defnode.db.gctransformer
            hdr = gct.gcheaderbuilder.header_of_object(top_container(defnode.obj))
            HDR = gct.gcheaderbuilder.HDR
            return [getattr(hdr, fldname) for fldname in HDR._names]
        else:
            return []

    def struct_gcheader_definition(self, defnode):
        return self.common_gcheader_definition(defnode)

    def struct_gcheader_initdata(self, defnode):
        return self.common_gcheader_initdata(defnode)

    def array_gcheader_definition(self, defnode):
        return self.common_gcheader_definition(defnode)

    def array_gcheader_initdata(self, defnode):
        return self.common_gcheader_initdata(defnode)

    def follow_rtti_dependencies(self, rtti):
        # Issue: the typeinfo corresponding to the rtti contains, as
        # destructor, a pointer to some ll_finalizer helper.  However it
        # is a delayed func pointer computed only in finish_helpers().
        # But we need to follow the regular destructor before
        # finish_helpers(), in case it uses new types.
        if rtti.destructor_funcptr is not None:
            self.db.get(rtti.destructor_funcptr)

    def struct_after_definition(self, defnode):
        return []

    def gc_libraries(self):
        return []

    def pre_pre_gc_code(self): # code that goes before include g_prerequisite.h
        return []

    def pre_gc_code(self):
        return ['typedef void *GC_hidden_pointer;']

    def gc_startup_code(self):
        return []

    # support for mapping weakref and rtti objects and types

    def convert_type(self, TYPE):
        if TYPE == lltype.RuntimeTypeInfo:
            return self.db.gctransformer.gcheaderbuilder.TYPEINFO
        elif TYPE == llmemory.WeakRef:
            return self.db.gctransformer.WEAKREFTYPE
        else:
            return TYPE

    def convert_prebuilt_object(self, obj):
        if isinstance(obj, lltype._rtti):
            self.follow_rtti_dependencies(obj)
            return self.db.gctransformer.convert_rtti(obj)._obj
        elif isinstance(obj, llmemory._wref):
            ptarget = obj._dereference()
            return self.db.gctransformer.convert_weakref_to(ptarget)._obj
        else:
            return obj

    def OP_GC_PUSH_ALIVE_PYOBJ(self, funcgen, op):
        expr = funcgen.expr(op.args[0])
        if expr == 'NULL':
            return ''
        return 'Py_XINCREF(%s);' % expr

    def OP_GC_POP_ALIVE_PYOBJ(self, funcgen, op):
        expr = funcgen.expr(op.args[0])
        return 'Py_XDECREF(%s);' % expr

    def OP_GC_SET_MAX_HEAP_SIZE(self, funcgen, op):
        return ''


class RefcountingGcPolicy(BasicGcPolicy):
    transformerclass = refcounting.RefcountingGCTransformer

    def OP_GC__COLLECT(self, funcgen, op):
        return ''


class BoehmGcPolicy(BasicGcPolicy):
    transformerclass = boehm.BoehmGCTransformer

    def gc_libraries(self):
        if sys.platform == 'win32':
            return ['gc_pypy']
        return ['gc']

    def pre_pre_gc_code(self):
        if sys.platform == "linux2":
            yield "#define _REENTRANT 1"
            yield "#define GC_LINUX_THREADS 1"
        if sys.platform != "win32":
            # GC_REDIRECT_TO_LOCAL is not supported on Win32 by gc6.8
            yield "#define GC_REDIRECT_TO_LOCAL 1"
        yield '#include <gc/gc.h>'
        yield '#define USING_BOEHM_GC'

    def pre_gc_code(self):
        return []

    def gc_startup_code(self):
        if sys.platform == 'win32':
            pass # yield 'assert(GC_all_interior_pointers == 0);'
        else:
            yield 'GC_all_interior_pointers = 0;'
        yield 'boehm_gc_startup_code();'

    def OP_GC__COLLECT(self, funcgen, op):
        return 'GC_gcollect();'

    def OP_GC_SET_MAX_HEAP_SIZE(self, funcgen, op):
        nbytes = funcgen.expr(op.args[0])
        return 'GC_set_max_heap_size(%s);' % (nbytes,)


# to get an idea how it looks like with no refcount/gc at all

class NoneGcPolicy(BoehmGcPolicy):

    gc_libraries = RefcountingGcPolicy.gc_libraries.im_func
    gc_startup_code = RefcountingGcPolicy.gc_startup_code.im_func

    def pre_pre_gc_code(self):
        yield '#define USING_NO_GC'


class FrameworkGcPolicy(BasicGcPolicy):
    transformerclass = framework.FrameworkGCTransformer

    def pre_pre_gc_code(self):
        yield '#define USING_FRAMEWORK_GC'

    def gc_startup_code(self):
        fnptr = self.db.gctransformer.frameworkgc_setup_ptr.value
        yield '%s();' % (self.db.get(fnptr),)

    def OP_GC_RELOAD_POSSIBLY_MOVED(self, funcgen, op):
        args = [funcgen.expr(v) for v in op.args]
        return '%s = %s; /* for moving GCs */' % (args[1], args[0])


class StacklessFrameworkGcPolicy(FrameworkGcPolicy):
    transformerclass = stacklessframework.StacklessFrameworkGCTransformer
    requires_stackless = True

class LLVMGcRootFrameworkGcPolicy(FrameworkGcPolicy):
    transformerclass = llvmgcroot.LLVMGcRootFrameworkGCTransformer

class AsmGcRootFrameworkGcPolicy(FrameworkGcPolicy):
    transformerclass = asmgcroot.AsmGcRootFrameworkGCTransformer


name_to_gcpolicy = {
    'boehm': BoehmGcPolicy,
    'ref': RefcountingGcPolicy,
    'none': NoneGcPolicy,
    'framework': FrameworkGcPolicy,
    'framework+stacklessgc': StacklessFrameworkGcPolicy,
    'framework+llvmgcroot': LLVMGcRootFrameworkGcPolicy,
    'framework+asmgcroot': AsmGcRootFrameworkGcPolicy,
}


