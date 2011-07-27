from pypy.rpython.rtyper import LowLevelOpList
from pypy.rpython.memory.gctransform.framework import BaseRootWalker
from pypy.rpython.memory.gctransform.framework import sizeofaddr
from pypy.rpython import rmodel
from pypy.rlib.debug import ll_assert
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.tool.algo.regalloc import perform_register_allocation
from pypy.translator.backendopt.ssa import DataFlowFamilyBuilder
from pypy.translator.unsimplify import copyvar, insert_empty_block
from pypy.objspace.flow.model import Block, Link, Constant
from pypy.objspace.flow.model import checkgraph, mkentrymap
from pypy.annotation import model as annmodel


class ShadowStackRootWalker(BaseRootWalker):
    need_root_stack = True
    collect_stacks_from_other_threads = None

    def __init__(self, gctransformer):
        BaseRootWalker.__init__(self, gctransformer)
        self.rootstacksize = sizeofaddr * gctransformer.root_stack_depth
        # NB. 'self' is frozen, but we can use self.gcdata to store state
        gcdata = self.gcdata

        def incr_stack(n):
            top = gcdata.root_stack_top
            gcdata.root_stack_top = top + n*sizeofaddr
            return top
        self.incr_stack = incr_stack

        def decr_stack(n):
            top = gcdata.root_stack_top - n*sizeofaddr
            gcdata.root_stack_top = top
            return top
        self.decr_stack = decr_stack

        def get_stack_top():
            return gcdata.root_stack_top
        self.get_stack_top = get_stack_top

        self.rootstackhook = gctransformer.root_stack_jit_hook
        if self.rootstackhook is None:
            def collect_stack_root(callback, gc, addr):
                if gc.points_to_valid_gc_object(addr):
                    callback(gc, addr)
                return sizeofaddr
            self.rootstackhook = collect_stack_root

    def push_stack(self, addr):
        top = self.incr_stack(1)
        top.address[0] = addr

    def pop_stack(self):
        top = self.decr_stack(1)
        return top.address[0]

    def allocate_stack(self):
        return llmemory.raw_malloc(self.rootstacksize)

    def setup_root_walker(self):
        stackbase = self.allocate_stack()
        ll_assert(bool(stackbase), "could not allocate root stack")
        self.gcdata.root_stack_top  = stackbase
        self.gcdata.root_stack_base = stackbase
        BaseRootWalker.setup_root_walker(self)

    def walk_stack_roots(self, collect_stack_root):
        gcdata = self.gcdata
        gc = self.gc
        rootstackhook = self.rootstackhook
        addr = gcdata.root_stack_base
        end = gcdata.root_stack_top
        while addr != end:
            addr += rootstackhook(collect_stack_root, gc, addr)
        if self.collect_stacks_from_other_threads is not None:
            self.collect_stacks_from_other_threads(collect_stack_root)

    def need_thread_support(self, gctransformer, getfn):
        from pypy.module.thread import ll_thread    # xxx fish
        from pypy.rpython.memory.support import AddressDict
        from pypy.rpython.memory.support import copy_without_null_values
        gcdata = self.gcdata
        # the interfacing between the threads and the GC is done via
        # three completely ad-hoc operations at the moment:
        # gc_thread_prepare, gc_thread_run, gc_thread_die.
        # See docstrings below.

        def get_aid():
            """Return the thread identifier, cast to an (opaque) address."""
            return llmemory.cast_int_to_adr(ll_thread.get_ident())

        def thread_setup():
            """Called once when the program starts."""
            aid = get_aid()
            gcdata.main_thread = aid
            gcdata.active_thread = aid
            gcdata.thread_stacks = AddressDict()     # {aid: root_stack_top}
            gcdata._fresh_rootstack = llmemory.NULL
            gcdata.dead_threads_count = 0

        def thread_prepare():
            """Called just before thread.start_new_thread().  This
            allocates a new shadow stack to be used by the future
            thread.  If memory runs out, this raises a MemoryError
            (which can be handled by the caller instead of just getting
            ignored if it was raised in the newly starting thread).
            """
            if not gcdata._fresh_rootstack:
                gcdata._fresh_rootstack = self.allocate_stack()
                if not gcdata._fresh_rootstack:
                    raise MemoryError

        def thread_run():
            """Called whenever the current thread (re-)acquired the GIL.
            This should ensure that the shadow stack installed in
            gcdata.root_stack_top/root_stack_base is the one corresponding
            to the current thread.
            """
            aid = get_aid()
            if gcdata.active_thread != aid:
                switch_shadow_stacks(aid)

        def thread_die():
            """Called just before the final GIL release done by a dying
            thread.  After a thread_die(), no more gc operation should
            occur in this thread.
            """
            aid = get_aid()
            if aid == gcdata.main_thread:
                return   # ignore calls to thread_die() in the main thread
                         # (which can occur after a fork()).
            gcdata.thread_stacks.setitem(aid, llmemory.NULL)
            old = gcdata.root_stack_base
            if gcdata._fresh_rootstack == llmemory.NULL:
                gcdata._fresh_rootstack = old
            else:
                llmemory.raw_free(old)
            install_new_stack(gcdata.main_thread)
            # from time to time, rehash the dictionary to remove
            # old NULL entries
            gcdata.dead_threads_count += 1
            if (gcdata.dead_threads_count & 511) == 0:
                copy = copy_without_null_values(gcdata.thread_stacks)
                gcdata.thread_stacks.delete()
                gcdata.thread_stacks = copy

        def switch_shadow_stacks(new_aid):
            save_away_current_stack()
            install_new_stack(new_aid)
        switch_shadow_stacks._dont_inline_ = True

        def save_away_current_stack():
            old_aid = gcdata.active_thread
            # save root_stack_base on the top of the stack
            self.push_stack(gcdata.root_stack_base)
            # store root_stack_top into the dictionary
            gcdata.thread_stacks.setitem(old_aid, gcdata.root_stack_top)

        def install_new_stack(new_aid):
            # look for the new stack top
            top = gcdata.thread_stacks.get(new_aid, llmemory.NULL)
            if top == llmemory.NULL:
                # first time we see this thread.  It is an error if no
                # fresh new stack is waiting.
                base = gcdata._fresh_rootstack
                gcdata._fresh_rootstack = llmemory.NULL
                ll_assert(base != llmemory.NULL, "missing gc_thread_prepare")
                gcdata.root_stack_top = base
                gcdata.root_stack_base = base
            else:
                # restore the root_stack_base from the top of the stack
                gcdata.root_stack_top = top
                gcdata.root_stack_base = self.pop_stack()
            # done
            gcdata.active_thread = new_aid

        def collect_stack(aid, stacktop, callback):
            if stacktop != llmemory.NULL and aid != gcdata.active_thread:
                # collect all valid stacks from the dict (the entry
                # corresponding to the current thread is not valid)
                gc = self.gc
                rootstackhook = self.rootstackhook
                end = stacktop - sizeofaddr
                addr = end.address[0]
                while addr != end:
                    addr += rootstackhook(callback, gc, addr)

        def collect_more_stacks(callback):
            ll_assert(get_aid() == gcdata.active_thread,
                      "collect_more_stacks(): invalid active_thread")
            gcdata.thread_stacks.foreach(collect_stack, callback)

        def _free_if_not_current(aid, stacktop, _):
            if stacktop != llmemory.NULL and aid != gcdata.active_thread:
                end = stacktop - sizeofaddr
                base = end.address[0]
                llmemory.raw_free(base)

        def thread_after_fork(result_of_fork, opaqueaddr):
            # we don't need a thread_before_fork in this case, so
            # opaqueaddr == NULL.  This is called after fork().
            if result_of_fork == 0:
                # We are in the child process.  Assumes that only the
                # current thread survived, so frees the shadow stacks
                # of all the other ones.
                gcdata.thread_stacks.foreach(_free_if_not_current, None)
                # Clears the dict (including the current thread, which
                # was an invalid entry anyway and will be recreated by
                # the next call to save_away_current_stack()).
                gcdata.thread_stacks.clear()
                # Finally, reset the stored thread IDs, in case it
                # changed because of fork().  Also change the main
                # thread to the current one (because there is not any
                # other left).
                aid = get_aid()
                gcdata.main_thread = aid
                gcdata.active_thread = aid

        self.thread_setup = thread_setup
        self.thread_prepare_ptr = getfn(thread_prepare, [], annmodel.s_None)
        self.thread_run_ptr = getfn(thread_run, [], annmodel.s_None,
                                    inline=True)
        # no thread_start_ptr here
        self.thread_die_ptr = getfn(thread_die, [], annmodel.s_None)
        # no thread_before_fork_ptr here
        self.thread_after_fork_ptr = getfn(thread_after_fork,
                                           [annmodel.SomeInteger(),
                                            annmodel.SomeAddress()],
                                           annmodel.s_None)
        self.collect_stacks_from_other_threads = collect_more_stacks


    def postprocess_graph(self, gct, graph):
        """Collect information about the gc_push_roots and gc_pop_roots
        added in this complete graph, and replace them with real operations.
        """
        #
        # Use the SSA builder to find "spans" of variables that come from a
        # single point but may extend over several blocks.
        spans = DataFlowFamilyBuilder(graph).get_variable_families()
        interesting_vars = set()
        for block in graph.iterblocks():
            for op in block.operations:
                if op.opname in ('gc_push_roots', 'gc_pop_roots'):
                    for v in op.args:
                        if isinstance(v, Constant):
                            continue
                        interesting_vars.add(spans.find_rep(v))
        if not interesting_vars:
            return
        #
        # ---------------------------------------------------
        #
        def is_interesting(v):
            return spans.find_rep(v) in interesting_vars
        regalloc = perform_register_allocation(graph, is_interesting)
        #
        # Compute the set of "useless stores", i.e. the Variables in the
        # gc_push_roots that are storing the same value as the one previously
        # loaded from the same index.
        useless_stores = self.compute_useless_stores(gct, graph, spans,
                                                     regalloc)
        #
        # We replace gc_push_roots/gc_pop_roots with individual
        # operations raw_store/raw_load
        blocks_push_roots = {}    # {block: index-of-the-first}
        blocks_pop_roots = {}     # {block: index-just-after-the-last}
        negnumcolors = 0
        c_type = rmodel.inputconst(lltype.Void, llmemory.Address)
        for block in graph.iterblocks():
            if block.operations == ():
                continue
            llops = LowLevelOpList()
            for op in block.operations:
                if op.opname not in ("gc_push_roots", "gc_pop_roots"):
                    llops.append(op)
                    continue
                top_addr = None
                for v in op.args:
                    if isinstance(v, Constant):
                        continue
                    if op.opname == "gc_push_roots":
                        blocks_push_roots.setdefault(block, len(llops))
                    if top_addr is None:
                        top_addr = llops.genop("direct_call",
                                               [gct.get_stack_top_ptr],
                                               resulttype=llmemory.Address)
                    k = ~regalloc.getcolor(v)
                    negnumcolors = min(negnumcolors, k)
                    c_k = rmodel.inputconst(lltype.Signed, k)
                    if op.opname == "gc_push_roots":
                        if (block, op, v) not in useless_stores:
                            llops.genop("raw_store", [top_addr, c_type,
                                                      c_k, v])
                    else:
                        v_newaddr = llops.genop("raw_load",
                                                [top_addr, c_type, c_k],
                                                resulttype=llmemory.Address)
                        llops.genop("gc_reload_possibly_moved", [v_newaddr, v])
                        blocks_pop_roots[block] = len(llops)
            block.operations[:] = llops
        numcolors = -negnumcolors
        c_numcolors = rmodel.inputconst(lltype.Signed, numcolors)
        #
        # For each block, determine in which category it is:
        #
        #  - dead: the block does not contain any gc_push_roots/gc_pop_roots
        #    and is not between two non-dead blocks
        #
        #  - start: the block contains gc_push_roots, and all blocks
        #    leading to it are dead
        #
        #  - stop: the block contains gc_pop_roots, and all blocks it
        #    goes to are dead
        #
        #  - startstop: the block is both starting and stopping
        #
        #  - alive: all other blocks
        #
        # The idea is to delay "incr_stack()" because sometimes the function
        # has fast paths that don't call anything else.  Also, it is important
        # to delay it for functions that start without having the GIL, and only
        # acquire it as they progress.
        #
        # Note that it is possible to transition directly from "dead" to
        # "alive" or back; some graphs may not have any "start" or "stop"
        # blocks.
        #
        blockstate = {}
        push_roots_and_down = self.close_downwards(graph, blocks_push_roots)
        pop_roots_and_up = self.close_upwards(graph, blocks_pop_roots)
        assert push_roots_and_down.issuperset(blocks_pop_roots)
        assert pop_roots_and_up.issuperset(blocks_push_roots)
        # dead blocks are the ones that are not in both sets at once
        non_dead_blocks = set()
        for block in graph.iterblocks():
            if block in push_roots_and_down and block in pop_roots_and_up:
                non_dead_blocks.add(block)
            else:
                blockstate[block] = "dead"
        #
        entrymap = mkentrymap(graph)
        for block in blocks_push_roots:
            for link in entrymap[block]:
                if link.prevblock in non_dead_blocks:
                    break
            else:
                assert block not in blockstate
                blockstate[block] = "start"
        for block in blocks_pop_roots:
            for link in block.exits:
                if link.target in non_dead_blocks:
                    break
            else:
                prev = blockstate.get(block, "")
                assert prev in ("", "start")
                blockstate[block] = prev + "stop"
        #
        for block in graph.iterblocks():
            blockstate.setdefault(block, "alive")
        #
        # If graph.startblock is "alive", then we need a new startblock
        # in which to put the "incr_stack()" operation later
        if blockstate[graph.startblock] == "alive":
            insert_empty_startblock(gct.translator.annotator, graph)
            blocks_push_roots[graph.startblock] = 0
            blockstate[graph.startblock] = "start"
        #
        # Now detect direct transitions from "dead" to "alive", and
        # insert new "start" blocks along the links.  Similarly, detect
        # direct transitions from "alive" to "dead" and put a "stop" block.
        for block in blockstate.keys():
            if blockstate[block] == "dead":
                for link in block.exits:
                    if blockstate[link.target] == "alive":
                        newblock = insert_empty_block(gct.translator.annotator,
                                                      link)
                        blocks_push_roots[newblock] = 0
                        blockstate[newblock] = "start"
            if blockstate[block] == "alive":
                for link in block.exits:
                    if blockstate[link.target] == "dead":
                        newblock = insert_empty_block(gct.translator.annotator,
                                                      link)
                        blocks_pop_roots[newblock] = 0
                        blockstate[newblock] = "stop"
        #
        # Now we can put "incr_stack(); fill with zeroes" in all "start"
        # blocks; similarly, we put "decr_stack()" in all "stop" blocks.
        for block in blockstate:
            if "stop" in blockstate[block]:     # "stop" or "startstop"
                llops = LowLevelOpList()
                llops.genop("direct_call", [gct.decr_stack_ptr, c_numcolors],
                            resulttype=llmemory.Address)
                i = blocks_pop_roots[block]
                llops.genop("_d_decr", [])
                block.operations[i:i] = llops
                # ^^^ important: done first, in case it's a startstop block,
                #     otherwise the index in 'blocks_push_roots[block]' is
                #     off by one
            if "start" in blockstate[block]:    # "start" or "startstop"
                llops = LowLevelOpList()
                llops.genop("_d_incr", [])
                llops.genop("direct_call", [gct.incr_stack_ptr, c_numcolors],
                            resulttype=llmemory.Address)
                top_addr = llops.genop("direct_call",
                                       [gct.get_stack_top_ptr],
                                       resulttype=llmemory.Address)
                c_null = rmodel.inputconst(llmemory.Address, llmemory.NULL)
                for k in range(numcolors):
                    c_k = rmodel.inputconst(lltype.Signed, ~k)
                    llops.genop("raw_store", [top_addr, c_type, c_k, c_null])
                i = blocks_push_roots[block]
                block.operations[i:i] = llops
        #
        checkgraph(graph)


    def compute_useless_stores(self, gct, graph, spans, regalloc):
        # A "useless store" is a Variable in a gc_push_roots instruction
        # that is the "same" one, in all paths, as the one loaded by a
        # previous gc_pop_roots.  Two variables v and w are the "same"
        # if spans.find_rep(v) is spans.find_rep(w).
        entrymap = mkentrymap(graph)
        #
        def enumerate_previous_gc_pop_roots(block, index):
            result = []
            seen = set()
            pending = [(block, index)]
            while pending:
                block, index = pending.pop()
                for i in range(index-1, -1, -1):
                    if block.operations[i].opname == 'gc_pop_roots':
                        # found gc_pop_roots, record it and stop
                        result.append(block.operations[i])
                        break
                else:
                    # find all blocks that go into this one
                    if block is graph.startblock:
                        return None
                    for link in entrymap[block]:
                        prevblock = link.prevblock
                        if prevblock in seen:
                            continue
                        seen.add(prevblock)
                        pending.append((prevblock, len(prevblock.operations)))
            return result
        #
        useless = {}
        for block in graph.iterblocks():
            for i, op in enumerate(block.operations):
                if op.opname == 'gc_push_roots':
                    result = enumerate_previous_gc_pop_roots(block, i)
                    if not result:
                        continue
                    for v in op.args:
                        if isinstance(v, Constant):
                            continue
                        vrep = spans.find_rep(v)
                        # check if 'v' is in all prevop.args
                        for prevop in result:
                            for w in prevop.args:
                                # if we find 'v' in this prevop.args, we
                                # can reuse it if it maps to the same index
                                if (spans.find_rep(w) is vrep
                                    and regalloc.getcolor(v) ==
                                        regalloc.getcolor(w)):
                                    break
                            else:
                                break   # did not find 'v' in this prevop.args
                        else:
                            # yes, found 'v' in each prevop.args.
                            useless[block, op, v] = True
                            gct.num_raw_store_avoided += 1
        return useless


    def close_downwards(self, graph, blockset):
        blockset = set(blockset)
        pending = list(blockset)
        while pending:
            block1 = pending.pop()
            for link in block1.exits:
                block2 = link.target
                if block2 not in blockset:
                    blockset.add(block2)
                    pending.append(block2)
        return blockset

    def close_upwards(self, graph, blockset):
        blockset = set(blockset)
        pending = list(blockset)
        entrymap = mkentrymap(graph)
        while pending:
            block1 = pending.pop()
            for link in entrymap[block1]:
                block2 = link.prevblock
                if block2 and block2 not in blockset:
                    blockset.add(block2)
                    pending.append(block2)
        return blockset
