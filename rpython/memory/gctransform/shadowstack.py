from rpython.annotator import model as annmodel
from rpython.rlib.debug import ll_assert
from rpython.rlib.nonconst import NonConstant
from rpython.rlib import rgc
from rpython.rtyper import rmodel
from rpython.rtyper.annlowlevel import llhelper
from rpython.rtyper.lltypesystem import lltype, llmemory, rffi
from rpython.rtyper.lltypesystem.lloperation import llop
from rpython.memory.gctransform.framework import (
     BaseFrameworkGCTransformer, BaseRootWalker, sizeofaddr)
from rpython.rtyper.rbuiltin import gen_cast


class ShadowStackFrameworkGCTransformer(BaseFrameworkGCTransformer):
    def annotate_walker_functions(self, getfn):
        pass

    def build_root_walker(self):
        return ShadowStackRootWalker(self)

    def push_roots(self, hop, keep_current_args=False):
        livevars = self.get_livevars_for_roots(hop, keep_current_args)
        self.num_pushs += len(livevars)
        hop.genop("shadowstack_push", list(livevars))    # may be 0
        return livevars

    def pop_roots(self, hop, livevars):
        if not livevars:
            return
        hop.genop("shadowstack_pop", list(livevars))


class ShadowStackRootWalker(BaseRootWalker):
    def __init__(self, gctransformer):
        BaseRootWalker.__init__(self, gctransformer)
        # NB. 'self' is frozen, but we can use self.gcdata to store state
        gcdata = self.gcdata

    def walk_stack_roots(self, collect_stack_root):
        WORD = llmemory.sizeof(llmemory.Address)
        r15 = llop.shadowstack_r15(lltype.Signed)
        gc = self.gc
        while r15 != -1:
            n = (r15 & 7) + 1
            r15 &= ~7
            while n > 0:
                addr = rffi.cast(llmemory.Address, r15 + n * WORD)
                collect_stack_root(gc, addr)
                n -= 1
            r15 = rffi.cast(llmemory.Address, r15).signed[0]

    def need_thread_support(self, gctransformer, getfn):
        xxxxxxxxx
        from rpython.rlib import rthread    # xxx fish
        gcdata = self.gcdata
        # the interfacing between the threads and the GC is done via
        # two completely ad-hoc operations at the moment:
        # gc_thread_run and gc_thread_die.  See docstrings below.

        shadow_stack_pool = self.shadow_stack_pool
        SHADOWSTACKREF = get_shadowstackref(self, gctransformer)

        # this is a dict {tid: SHADOWSTACKREF}, where the tid for the
        # current thread may be missing so far
        gcdata.thread_stacks = None

        # Return the thread identifier, as an integer.
        get_tid = rthread.get_ident

        def thread_setup():
            tid = get_tid()
            gcdata.main_tid = tid
            gcdata.active_tid = tid

        def thread_run():
            """Called whenever the current thread (re-)acquired the GIL.
            This should ensure that the shadow stack installed in
            gcdata.root_stack_top/root_stack_base is the one corresponding
            to the current thread.
            No GC operation here, e.g. no mallocs or storing in a dict!
            """
            tid = get_tid()
            if gcdata.active_tid != tid:
                switch_shadow_stacks(tid)

        def thread_die():
            """Called just before the final GIL release done by a dying
            thread.  After a thread_die(), no more gc operation should
            occur in this thread.
            """
            tid = get_tid()
            if tid == gcdata.main_tid:
                return   # ignore calls to thread_die() in the main thread
                         # (which can occur after a fork()).
            # we need to switch somewhere else, so go to main_tid
            gcdata.active_tid = gcdata.main_tid
            thread_stacks = gcdata.thread_stacks
            new_ref = thread_stacks[gcdata.active_tid]
            try:
                del thread_stacks[tid]
            except KeyError:
                pass
            # no more GC operation from here -- switching shadowstack!
            shadow_stack_pool.forget_current_state()
            shadow_stack_pool.restore_state_from(new_ref)

        def switch_shadow_stacks(new_tid):
            # we have the wrong shadowstack right now, but it should not matter
            thread_stacks = gcdata.thread_stacks
            try:
                if thread_stacks is None:
                    gcdata.thread_stacks = thread_stacks = {}
                    raise KeyError
                new_ref = thread_stacks[new_tid]
            except KeyError:
                new_ref = lltype.nullptr(SHADOWSTACKREF)
            try:
                old_ref = thread_stacks[gcdata.active_tid]
            except KeyError:
                # first time we ask for a SHADOWSTACKREF for this active_tid
                old_ref = shadow_stack_pool.allocate(SHADOWSTACKREF)
                thread_stacks[gcdata.active_tid] = old_ref
            #
            # no GC operation from here -- switching shadowstack!
            shadow_stack_pool.save_current_state_away(old_ref, llmemory.NULL)
            if new_ref:
                shadow_stack_pool.restore_state_from(new_ref)
            else:
                shadow_stack_pool.start_fresh_new_state()
            # done
            #
            gcdata.active_tid = new_tid
        switch_shadow_stacks._dont_inline_ = True

        def thread_after_fork(result_of_fork, opaqueaddr):
            # we don't need a thread_before_fork in this case, so
            # opaqueaddr == NULL.  This is called after fork().
            if result_of_fork == 0:
                # We are in the child process.  Assumes that only the
                # current thread survived, so frees the shadow stacks
                # of all the other ones.
                gcdata.thread_stacks = None
                # Finally, reset the stored thread IDs, in case it
                # changed because of fork().  Also change the main
                # thread to the current one (because there is not any
                # other left).
                tid = get_tid()
                gcdata.main_tid = tid
                gcdata.active_tid = tid

        self.thread_setup = thread_setup
        self.thread_run_ptr = getfn(thread_run, [], annmodel.s_None,
                                    inline=True, minimal_transform=False)
        self.thread_die_ptr = getfn(thread_die, [], annmodel.s_None,
                                    minimal_transform=False)
        # no thread_before_fork_ptr here
        self.thread_after_fork_ptr = getfn(thread_after_fork,
                                           [annmodel.SomeInteger(),
                                            annmodel.SomeAddress()],
                                           annmodel.s_None,
                                           minimal_transform=False)

    def need_stacklet_support(self, gctransformer, getfn):
        xxxxxxxxxxxxx
        shadow_stack_pool = self.shadow_stack_pool
        SHADOWSTACKREF = get_shadowstackref(self, gctransformer)

        def gc_shadowstackref_new():
            ssref = shadow_stack_pool.allocate(SHADOWSTACKREF)
            return lltype.cast_opaque_ptr(llmemory.GCREF, ssref)

        def gc_shadowstackref_context(gcref):
            ssref = lltype.cast_opaque_ptr(lltype.Ptr(SHADOWSTACKREF), gcref)
            return ssref.context

        def gc_save_current_state_away(gcref, ncontext):
            ssref = lltype.cast_opaque_ptr(lltype.Ptr(SHADOWSTACKREF), gcref)
            shadow_stack_pool.save_current_state_away(ssref, ncontext)

        def gc_forget_current_state():
            shadow_stack_pool.forget_current_state()

        def gc_restore_state_from(gcref):
            ssref = lltype.cast_opaque_ptr(lltype.Ptr(SHADOWSTACKREF), gcref)
            shadow_stack_pool.restore_state_from(ssref)

        def gc_start_fresh_new_state():
            shadow_stack_pool.start_fresh_new_state()

        s_gcref = annmodel.SomePtr(llmemory.GCREF)
        s_addr = annmodel.SomeAddress()
        self.gc_shadowstackref_new_ptr = getfn(gc_shadowstackref_new,
                                               [], s_gcref,
                                               minimal_transform=False)
        self.gc_shadowstackref_context_ptr = getfn(gc_shadowstackref_context,
                                                   [s_gcref], s_addr,
                                                   inline=True)
        self.gc_save_current_state_away_ptr = getfn(gc_save_current_state_away,
                                                    [s_gcref, s_addr],
                                                    annmodel.s_None,
                                                    inline=True)
        self.gc_forget_current_state_ptr = getfn(gc_forget_current_state,
                                                 [], annmodel.s_None,
                                                 inline=True)
        self.gc_restore_state_from_ptr = getfn(gc_restore_state_from,
                                               [s_gcref], annmodel.s_None,
                                               inline=True)
        self.gc_start_fresh_new_state_ptr = getfn(gc_start_fresh_new_state,
                                                  [], annmodel.s_None,
                                                  inline=True)

# ____________________________________________________________
