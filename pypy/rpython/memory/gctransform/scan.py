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

    def __init__(self, gctransformer):
        BaseRootWalker.__init__(self, gctransformer)

        def _asm_callback():
            self.walk_stack_from()
        self._asm_callback = _asm_callback

    #def need_stacklet_support(self, gctransformer, getfn):
    #   anything needed?

    #def need_thread_support(self, gctransformer, getfn):
    #   xxx

    def walk_stack_roots(self, collect_stack_root):
        gcdata = self.gcdata
        gcdata._gc_collect_stack_root = collect_stack_root
        pypy_asm_close_for_scanning(
            llhelper(ASM_CALLBACK_PTR, self._asm_callback))

    def walk_stack_from(self):
        raise NotImplementedError


eci = ExternalCompilationInfo(
    post_include_bits = ["extern void pypy_asm_close_for_scanning(void*);\n"],
    separate_module_sources = ['''

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
