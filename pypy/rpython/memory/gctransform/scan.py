from pypy.rpython.memory.gctransform.framework import FrameworkGCTransformer
from pypy.rpython.memory.gctransform.framework import BaseRootWalker
from pypy.translator.tool.cbuild import ExternalCompilationInfo
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.rpython.annlowlevel import llhelper


class ScanFrameworkGCTransformer(FrameworkGCTransformer):

    def push_roots(self, hop, keep_current_args=False):
        livevars = self.get_livevars_for_roots(hop, keep_current_args)
        self.num_pushs += len(livevars)
        return livevars

    def pop_roots(self, hop, livevars):
        if not livevars:
            return
        # mark the values as keepalives if they can point to var-sized objs
        for var in livevars:
            if self.can_point_to_varsized(var.concretetype):
                hop.genop("keepalive", [var])

    def can_point_to_varsized(self, TYPE):
        if not isinstance(TYPE, lltype.Ptr) or TYPE.TO._gckind != "gc":
            return False      # not a ptr-to-gc type at all
        # this is where we use the fact that a GcStruct cannot inherit another
        # GcStruct *and* add an _arrayfld:
        if isinstance(TYPE.TO, lltype.GcStruct) and TYPE.TO._arrayfld is None:
            return False      # can point only to a GcStruct with no _arrayfld
        else:
            return True       # other, including GCREF

    def build_root_walker(self):
        return ScanStackRootWalker(self)


class ScanStackRootWalker(BaseRootWalker):
    conservative_stack_roots = True

    def __init__(self, gctransformer):
        BaseRootWalker.__init__(self, gctransformer)

        def _asm_callback():
            self.walk_stack_from()
        self._asm_callback = _asm_callback

    #def need_stacklet_support(self, gctransformer, getfn):
    #   xxx

    #def need_thread_support(self, gctransformer, getfn):
    #   xxx

    def walk_stack_roots(self, collect_stack_root_range):
        gcdata = self.gcdata
        gcdata._gc_collect_stack_root_range = collect_stack_root_range
        pypy_asm_close_for_scanning(
            llhelper(ASM_CALLBACK_PTR, self._asm_callback))

    def walk_stack_from(self):
        bottom = pypy_get_asm_tmp_stack_bottom()    # highest address
        top = pypy_get_asm_stackptr()               # lowest address
        collect_stack_root_range = self.gcdata._gc_collect_stack_root_range
        collect_stack_root_range(self.gc, top, bottom)


eci = ExternalCompilationInfo(
    post_include_bits = ['''
extern void pypy_asm_close_for_scanning(void*);
extern void *pypy_asm_tmp_stack_bottom;
#define pypy_get_asm_tmp_stack_bottom()  pypy_asm_tmp_stack_bottom

#if defined(__amd64__)
#  define _pypy_get_asm_stackptr(result)  asm("movq %%rsp, %0" : "=g"(result))
#else
#  define _pypy_get_asm_stackptr(result)  asm("movl %%esp, %0" : "=g"(result))
#endif

static void *pypy_get_asm_stackptr(void)
{
    /* might return a "esp" whose value is slightly smaller than necessary,
       due to the extra function call. */
    void *result;
    _pypy_get_asm_stackptr(result);
    return result;
}

'''],
    separate_module_sources = ['''

void *pypy_asm_tmp_stack_bottom = 0;    /* temporary */

void pypy_asm_close_for_scanning(void *fn)
{
    /* We have to do the call by clobbering all registers.  This is
       needed to ensure that all GC pointers are forced on the stack. */
#if defined(__amd64__)
    asm volatile("call *%%rsi" : : "rsi"(fn) :
                 "memory", "rax", "rbx", "rcx", "rdx", "rbp", "rdi",
                 "r8", "r9", "r10", "r11", "r12", "r13", "r14", "r15");
#else
    asm volatile("call *%%eax" : : "eax"(fn) :
                 "memory", "ebx", "ecx", "edx", "ebp", "esi", "edi");
#endif
}
'''],
    )

ASM_CALLBACK_PTR = lltype.Ptr(lltype.FuncType([], lltype.Void))

pypy_asm_close_for_scanning = rffi.llexternal('pypy_asm_close_for_scanning',
                                              [ASM_CALLBACK_PTR], lltype.Void,
                                              sandboxsafe=True,
                                              _nowrapper=True,
                                              random_effects_on_gcobjs=True,
                                              compilation_info=eci)
pypy_get_asm_tmp_stack_bottom =rffi.llexternal('pypy_get_asm_tmp_stack_bottom',
                                               [], llmemory.Address,
                                               sandboxsafe=True,
                                               _nowrapper=True,
                                               compilation_info=eci)
pypy_get_asm_stackptr = rffi.llexternal('pypy_get_asm_stackptr',
                                        [], llmemory.Address,
                                        sandboxsafe=True,
                                        _nowrapper=True,
                                        compilation_info=eci)
