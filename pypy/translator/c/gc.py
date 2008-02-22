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

    # for rtti node
    def get_real_rtti_type(self):
        return self.db.gctransformer.gcheaderbuilder.TYPEINFO

    def convert_rtti(self, obj):
        return self.db.gctransformer.convert_rtti(obj)

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

    def get_real_weakref_type(self):
        return boehm.WEAKLINK

    def convert_weakref_to(self, ptarget):
        return boehm.convert_weakref_to(ptarget)

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

    def get_real_weakref_type(self):
        return framework.WEAKREF

    def convert_weakref_to(self, ptarget):
        return framework.convert_weakref_to(ptarget)

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


