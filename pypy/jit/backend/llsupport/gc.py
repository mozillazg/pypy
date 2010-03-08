from pypy.rpython.lltypesystem import lltype, llmemory, rffi, rstr
from pypy.jit.backend.llsupport import symbolic
from pypy.jit.backend.llsupport.symbolic import WORD
from pypy.jit.backend.llsupport.descr import BaseSizeDescr, BaseArrayDescr
from pypy.jit.backend.llsupport.descr import GcCache

# ____________________________________________________________

class GcLLDescription(GcCache):
    def __init__(self, gcdescr, translator=None):
        GcCache.__init__(self, translator is not None)
        self.gcdescr = gcdescr
    def _freeze_(self):
        return True
    def initialize(self):
        pass
    def do_write_barrier(self, gcref_struct, gcref_newptr):
        pass
    def rewrite_assembler(self, cpu, operations):
        pass
    def can_inline_malloc(self, descr):
        return False
    def has_write_barrier_class(self):
        return None

# ____________________________________________________________

class GcLLDescr_boehm(GcLLDescription):
    moving_gc = False
    gcrootmap = None

    def __init__(self, gcdescr, translator):
        GcLLDescription.__init__(self, gcdescr, translator)
        # grab a pointer to the Boehm 'malloc' function
        from pypy.rpython.tool import rffi_platform
        compilation_info = rffi_platform.configure_boehm()

        # Versions 6.x of libgc needs to use GC_local_malloc().
        # Versions 7.x of libgc removed this function; GC_malloc() has
        # the same behavior if libgc was compiled with
        # THREAD_LOCAL_ALLOC.
        class CConfig:
            _compilation_info_ = compilation_info
            HAS_LOCAL_MALLOC = rffi_platform.Has("GC_local_malloc")
        config = rffi_platform.configure(CConfig)
        if config['HAS_LOCAL_MALLOC']:
            GC_MALLOC = "GC_local_malloc"
        else:
            GC_MALLOC = "GC_malloc"

        malloc_fn_ptr = rffi.llexternal(GC_MALLOC,
                                        [lltype.Signed], # size_t, but good enough
                                        llmemory.GCREF,
                                        compilation_info=compilation_info,
                                        sandboxsafe=True,
                                        _nowrapper=True)
        self.funcptr_for_new = malloc_fn_ptr

        # on some platform GC_init is required before any other
        # GC_* functions, call it here for the benefit of tests
        # XXX move this to tests
        init_fn_ptr = rffi.llexternal("GC_init",
                                      [], lltype.Void,
                                      compilation_info=compilation_info,
                                      sandboxsafe=True,
                                      _nowrapper=True)

        init_fn_ptr()

    def gc_malloc(self, sizedescr):
        assert isinstance(sizedescr, BaseSizeDescr)
        return self.funcptr_for_new(sizedescr.size)

    def gc_malloc_array(self, arraydescr, num_elem):
        assert isinstance(arraydescr, BaseArrayDescr)
        ofs_length = arraydescr.get_ofs_length(self.translate_support_code)
        basesize = arraydescr.get_base_size(self.translate_support_code)
        itemsize = arraydescr.get_item_size(self.translate_support_code)
        size = basesize + itemsize * num_elem
        res = self.funcptr_for_new(size)
        rffi.cast(rffi.CArrayPtr(lltype.Signed), res)[ofs_length/WORD] = num_elem
        return res

    def gc_malloc_str(self, num_elem):
        basesize, itemsize, ofs_length = symbolic.get_array_token(rstr.STR,
                                                   self.translate_support_code)
        assert itemsize == 1
        size = basesize + num_elem
        res = self.funcptr_for_new(size)
        rffi.cast(rffi.CArrayPtr(lltype.Signed), res)[ofs_length/WORD] = num_elem
        return res

    def gc_malloc_unicode(self, num_elem):
        basesize, itemsize, ofs_length = symbolic.get_array_token(rstr.UNICODE,
                                                   self.translate_support_code)
        size = basesize + num_elem * itemsize
        res = self.funcptr_for_new(size)
        rffi.cast(rffi.CArrayPtr(lltype.Signed), res)[ofs_length/WORD] = num_elem
        return res

    def args_for_new(self, sizedescr):
        assert isinstance(sizedescr, BaseSizeDescr)
        return [sizedescr.size]

    def get_funcptr_for_new(self):
        return self.funcptr_for_new

    get_funcptr_for_newarray = None
    get_funcptr_for_newstr = None
    get_funcptr_for_newunicode = None

# ____________________________________________________________

def GcLLDescr_framework(*args):
    from pypy.jit.backend.llsupport import gcframework
    return gcframework.GcLLDescr_framework(*args)

# ____________________________________________________________

def get_ll_description(gcdescr, translator=None):
    # translator is None if translate_support_code is False.
    if gcdescr is not None:
        name = gcdescr.config.translation.gctransformer
    else:
        name = "boehm"
    try:
        cls = globals()['GcLLDescr_' + name]
    except KeyError:
        raise NotImplementedError("GC transformer %r not supported by "
                                  "the JIT backend" % (name,))
    return cls(gcdescr, translator)
