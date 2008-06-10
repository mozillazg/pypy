import sys
from pypy.translator.c.support import cdecl
from pypy.translator.c.node import ContainerNode
from pypy.rpython.lltypesystem.lltype import \
     typeOf, Ptr, ContainerType, RttiStruct, \
     RuntimeTypeInfo, getRuntimeTypeInfo, top_container
from pypy.rpython.memory.gctransform import \
     refcounting, boehm, framework, llvmgcroot, asmgcroot
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.translator.tool.cbuild import ExternalCompilationInfo, CompilationSet

class BasicGcPolicy(object):
    requires_stackless = False
    
    def __init__(self, db, thread_enabled=False):
        self.db = db
        self.thread_enabled = thread_enabled

    def common_gcheader_definition(self, defnode):
        return []

    def common_gcheader_initdata(self, defnode):
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

    def compilation_info(self):
        return ExternalCompilationInfo()

    def pre_pre_gc_code(self): # code that goes before include g_prerequisite.h
        gct = self.db.gctransformer
        yield '/* using %s */' % (gct.__class__.__name__,)
        yield '#define MALLOC_ZERO_FILLED %d' % (gct.malloc_zero_filled,)

    def pre_gc_code(self):
        return ['typedef void *GC_hidden_pointer;']

    def gc_startup_code(self):
        return []

    def struct_setup(self, structdefnode, rtti):
        return None

    def array_setup(self, arraydefnode):
        return None

    def rtti_type(self):
        return ''

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

    def OP_GC_THREAD_PREPARE(self, funcgen, op):
        return ''

    def OP_GC_THREAD_RUN(self, funcgen, op):
        return ''

    def OP_GC_THREAD_DIE(self, funcgen, op):
        return ''


class RefcountingInfo:
    static_deallocator = None

from pypy.rlib.objectmodel import CDefinedIntSymbolic

class RefcountingGcPolicy(BasicGcPolicy):
    transformerclass = refcounting.RefcountingGCTransformer

    def common_gcheader_definition(self, defnode):
        if defnode.db.gctransformer is not None:
            HDR = defnode.db.gctransformer.HDR
            return [(name, HDR._flds[name]) for name in HDR._names]
        else:
            return []

    def common_gcheader_initdata(self, defnode):
        if defnode.db.gctransformer is not None:
            gct = defnode.db.gctransformer
            hdr = gct.gcheaderbuilder.header_of_object(top_container(defnode.obj))
            HDR = gct.HDR
            return [getattr(hdr, fldname) for fldname in HDR._names]
        else:
            return []

    # for structs

    def struct_setup(self, structdefnode, rtti):
        if rtti is not None:
            transformer = structdefnode.db.gctransformer
            fptr = transformer.static_deallocation_funcptr_for_type(
                structdefnode.STRUCT)
            structdefnode.gcinfo = RefcountingInfo()
            structdefnode.gcinfo.static_deallocator = structdefnode.db.get(fptr)

    # for arrays

    def array_setup(self, arraydefnode):
        pass

    # for rtti node

    def rtti_type(self):
        return 'void (@)(void *)'   # void dealloc_xx(struct xx *)

    def rtti_node_factory(self):
        return RefcountingRuntimeTypeInfo_OpaqueNode

    # zero malloc impl

    def OP_GC_CALL_RTTI_DESTRUCTOR(self, funcgen, op):
        args = [funcgen.expr(v) for v in op.args]
        line = '%s(%s);' % (args[0], ', '.join(args[1:]))
        return line     
    
    def OP_GC_FREE(self, funcgen, op):
        args = [funcgen.expr(v) for v in op.args]
        return 'OP_FREE(%s);' % (args[0], )    

    def OP_GC__COLLECT(self, funcgen, op):
        return ''

    def OP_GC__DISABLE_FINALIZERS(self, funcgen, op):
        return ''

    def OP_GC__ENABLE_FINALIZERS(self, funcgen, op):
        return ''


class RefcountingRuntimeTypeInfo_OpaqueNode(ContainerNode):
    nodekind = 'refcnt rtti'
    globalcontainer = True
    typename = 'void (@)(void *)'

    def __init__(self, db, T, obj):
        assert T == RuntimeTypeInfo
        assert isinstance(obj.about, RttiStruct)
        self.db = db
        self.T = T
        self.obj = obj
        defnode = db.gettypedefnode(obj.about)
        self.implementationtypename = 'void (@)(void *)'
        self.name = defnode.gcinfo.static_deallocator
        self.ptrname = '((void (*)(void *)) %s)' % (self.name,)

    def enum_dependencies(self):
        return []

    def implementation(self):
        return []



class BoehmInfo:
    finalizer = None


class BoehmGcPolicy(BasicGcPolicy):
    transformerclass = boehm.BoehmGCTransformer

    def array_setup(self, arraydefnode):
        pass

    def struct_setup(self, structdefnode, rtti):
        pass

    def rtti_type(self):
        return BoehmGcRuntimeTypeInfo_OpaqueNode.typename

    def rtti_node_factory(self):
        return BoehmGcRuntimeTypeInfo_OpaqueNode

    def compilation_info(self):
        from pypy.translator.tool.cbuild import external_dir

        # Get source:
        # http://www.hpl.hp.com/personal/Hans_Boehm/gc/gc_source/gc6.8.tar.gz
        # extract it into the "dist/external" directory
        gc_home = external_dir.join("gc6.8")

        if gc_home.check(dir=True):
            from pypy.tool.udir import udir
            udir.join('gc', 'gc.h').ensure()
            udir.join('gc', 'gc.h').write('#include "%s/include/gc.h"\n' % gc_home)

            if sys.platform == 'linux2':
                ccflags = ['-D_REENTRANT', '-DGC_LINUX_THREADS', '-DTHREAD_LOCAL_ALLOC']
                libraries = []
            elif sys.platform == 'win32':
                ccflags = ['-DGC_WIN32_THREADS', '-DGC_NOT_DLL']
                libraries = ['user32']

            if sys.platform != "win32":
                # GC_REDIRECT_TO_LOCAL is not supported on Win32 by gc6.8
                ccflags.append('-DGC_REDIRECT_TO_LOCAL')

            gc_eci = ExternalCompilationInfo(
                include_dirs=[gc_home.join('include')],
                compile_extra=ccflags + ['-DSILENT'],
                libraries=libraries,
            )

            cs = CompilationSet(gc_eci,
                files=[gc_home.join(x) for x in
                       ['malloc.c', 'mallocx.c', 'alloc.c',
                        'allchblk.c', 'new_hblk.c',
                        'finalize.c', 'reclaim.c',
                        'headers.c', 'obj_map.c', 'stubborn.c',
                        'mark.c', 'mark_rts.c', 'blacklst.c',
                        'misc.c', 'os_dep.c', 'mach_dep.c',
                        'dyn_load.c',
                        'win32_threads.c',
                        'pthread_support.c', 'pthread_stop_world.c',
                        'specific.c',
                        ]])

            eci = ExternalCompilationInfo(
                include_dirs=[udir],
                compile_extra=ccflags,
                extra_objects=cs.compile_objects(),
                libraries=libraries,
                )

        else:
            if sys.platform == 'win32':
                libraries = ['gc_pypy'],
            else:
                libraries = ['gc']

            eci = ExternalCompilationInfo(
                libraries=libraries,
            )

        return eci

    def pre_pre_gc_code(self):
        for line in BasicGcPolicy.pre_pre_gc_code(self):
            yield line
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

class BoehmGcRuntimeTypeInfo_OpaqueNode(ContainerNode):
    nodekind = 'boehm rtti'
    globalcontainer = True
    typename = 'char @'

    def __init__(self, db, T, obj):
        assert T == RuntimeTypeInfo
        assert isinstance(obj.about, RttiStruct)
        self.db = db
        self.T = T
        self.obj = obj
        defnode = db.gettypedefnode(obj.about)
        self.implementationtypename = self.typename
        self.name = self.db.namespace.uniquename('g_rtti_v_'+ defnode.barename)
        self.ptrname = '(&%s)' % (self.name,)

    def enum_dependencies(self):
        return []

    def implementation(self):
        yield 'char %s  /* uninitialized */;' % self.name

class FrameworkGcRuntimeTypeInfo_OpaqueNode(BoehmGcRuntimeTypeInfo_OpaqueNode):
    nodekind = 'framework rtti'


# to get an idea how it looks like with no refcount/gc at all

class NoneGcPolicy(BoehmGcPolicy):

    gc_startup_code = RefcountingGcPolicy.gc_startup_code.im_func


class FrameworkGcPolicy(BasicGcPolicy):
    transformerclass = framework.FrameworkGCTransformer

    def struct_setup(self, structdefnode, rtti):
        if rtti is not None and hasattr(rtti._obj, 'destructor_funcptr'):
            destrptr = rtti._obj.destructor_funcptr
            # make sure this is seen by the database early, i.e. before
            # finish_helpers() on the gctransformer
            self.db.get(destrptr)
            # the following, on the other hand, will only discover ll_finalizer
            # helpers.  The get() sees and records a delayed pointer.  It is
            # still important to see it so that it can be followed as soon as
            # the mixlevelannotator resolves it.
            gctransf = self.db.gctransformer
            fptr = gctransf.finalizer_funcptr_for_type(structdefnode.STRUCT)
            self.db.get(fptr)

    def array_setup(self, arraydefnode):
        pass

    def rtti_type(self):
        return FrameworkGcRuntimeTypeInfo_OpaqueNode.typename

    def rtti_node_factory(self):
        return FrameworkGcRuntimeTypeInfo_OpaqueNode

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

    def common_gcheader_definition(self, defnode):
        return defnode.db.gctransformer.gc_fields()

    def common_gcheader_initdata(self, defnode):
        o = top_container(defnode.obj)
        return defnode.db.gctransformer.gc_field_values_for(o)

class LLVMGcRootFrameworkGcPolicy(FrameworkGcPolicy):
    transformerclass = llvmgcroot.LLVMGcRootFrameworkGCTransformer

class AsmGcRootFrameworkGcPolicy(FrameworkGcPolicy):
    transformerclass = asmgcroot.AsmGcRootFrameworkGCTransformer


name_to_gcpolicy = {
    'boehm': BoehmGcPolicy,
    'ref': RefcountingGcPolicy,
    'none': NoneGcPolicy,
    'framework': FrameworkGcPolicy,
    'framework+llvmgcroot': LLVMGcRootFrameworkGcPolicy,
    'framework+asmgcroot': AsmGcRootFrameworkGcPolicy,
}


