"""
Interface to 'tealets' for RPython.

Note that you must translate with the --tealet option if you include
this file in your RPython program.
"""
from pypy.rpython.lltypesystem import lltype, llmemory, rffi
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.rpython.annlowlevel import llhelper
from pypy.rlib.debug import ll_assert
from pypy.rlib.objectmodel import we_are_translated

from pypy.rlib import _tealet_rffi


class TealetError(Exception):
    def __init__(self, msg):
        self.msg = msg


def _make_classes(base_class):

    class Tealet(base_class):
        lltealet = _tealet_rffi.NULL_TEALET
        _suspended_stack = NULL_SUSPSTACK

        def switch(self):
            _switch(self)

        def run(self):
            raise NotImplementedError

    class MainTealet(Tealet):
        def __init__(self):
            assert we_are_translated(), "no support for untranslated runs yet"
            self.main = self
            self.current = self
            self.lltealet = _tealet_rffi.tealet_initialize(_tealet_rffi.NULL)

        def __del__(self):
            _tealet_rffi.tealet_finalize(self.lltealet)

        def start(self, tealet):
            if tealet.lltealet:
                raise TealetError("tealet already running")
            tealet.main = self
            _new(self, tealet)

    return Tealet, MainTealet

## ------------------------------------------------------------
## The code below is implementation details.

## No support for multithreading!  The caller is responsible for not
## mixing threads.

class Switcher(object):
    current = None
    target = None
    exception = None
switcher = Switcher()

llswitcher = lltype.malloc(rffi.CArray(_tealet_rffi.TEALET_P), 1,
                           flavor='raw', zero=True)

def _new(main, starting_tealet):
    switcher.current = main.current
    switcher.target = starting_tealet
    llswitcher[0] = main.lltealet
    r = _stack_protected_call(llhelper(FUNCNOARG, _new_critical))
    _check_exception(r)

def _new_critical():
    # critical function: no gc operation, and no gc variable alive!
    llmain = llswitcher[0]
    llrun = llhelper(_tealet_rffi.TEALET_RUN_P, _run)
    llarg = _tealet_rffi.NULL
    return _tealet_rffi.tealet_new(llmain, llrun, llarg)

def _run(lltealet, llarg):
    llop.gc_stack_bottom(lltype.Void)
    # end of critical code: no gc operation before here!
    tealet = switcher.target
    switcher.current = None
    switcher.target = None
    tealet.lltealet = lltealet
    main = tealet.main
    main.current = tealet
    #
    try:
        other = tealet.run()
        if other is None:
            other = main
        if not other.lltealet:
            raise TealetError("returning to a dead tealet")
        if other.main is not main:
            raise TealetError("returning to a tealet in a different group")
    except Exception, e:
        other = main
        switcher.exception = e
    tealet.lltealet = _tealet_rffi.NULL_TEALET
    main.current = other
    switcher.target = other
    llresult = other.lltealet
    return llresult

def _switch(target):
    main = target.main
    switcher.current = main.current
    switcher.target = target
    main.current = target
    llswitcher[0] = target.lltealet
    r = _stack_protected_call(llhelper(FUNCNOARG, _switch_critical))
    _check_exception(r)

def _switch_critical():
    # critical code: no gc operation!
    lltarget = llswitcher[0]
    return _tealet_rffi.tealet_switch(lltarget)

def _check_exception(r):
    switcher.current = None
    switcher.target = None
    r = rffi.cast(lltype.Signed, r)
    if r != 0:
        # rare case: tealet.c complains, e.g. out of memory.  I think that
        # in this case it's not really possible to have 'exception != None'.
        # Clean it anyway to avoid it showing up at a random time later.
        switcher.exception = None
        raise TealetError("internal error %d" % r)
    e = switcher.exception
    if e is not None:
        switcher.exception = None
        raise e

# ____________________________________________________________
#
# AsmGcRoot stack walking.
# XXX rethink the interfacing with asmgcroot.py
#
# This is a copy of the logic in asmgcroot.py, rewritten so that all
# pointer reads from the stack go via _tealet_translate_pointer()
# and also rewritten in an iterator-like style, with a next() method
# that just returns the next stack pointer.
# XXX avoid copying so much of the logic of asmgcroot

_asmstackrootwalker = None    # BIG HACK: monkey-patched by asmgcroot.py
_tealetrootwalker = None

def get_tealetrootwalker():
    # lazily called, to make the following imports lazy
    global _tealetrootwalker
    if _tealetrootwalker is not None:
        return _tealetrootwalker

    from pypy.rpython.memory.gctransform.asmgcroot import (
        WALKFRAME, CALLEE_SAVED_REGS)

    assert _asmstackrootwalker is not None, "should have been monkey-patched"
    basewalker = _asmstackrootwalker

    class TealetRootWalker(object):
        _alloc_flavor_ = "raw"

        enumerating = False

        def setup(self, obj):
            # initialization: read the SUSPSTACK object
            p = llmemory.cast_adr_to_ptr(obj, lltype.Ptr(SUSPSTACK))
            if not p.context:
                return False
            self.context = p.context
            initialframedata = p.initialframedata
            del p
            self.curframe = lltype.malloc(WALKFRAME, flavor='raw')
            self.otherframe = lltype.malloc(WALKFRAME, flavor='raw')
            basewalker.fill_initial_frame(self.curframe, self.initialframedata)
            return True

        def teardown(self):
            lltype.free(self.curframe, flavor='raw')
            lltype.free(self.otherframe, flavor='raw')
            self.context = _tealet_rffi.NULL_TEALET
            return llmemory.NULL

        def next(self, obj, prev):
            #
            # Pointers to the stack can be "translated" or not:
            #
            #   * Non-translated pointers point to where the data would be
            #     if the stack was installed and running.
            #
            #   * Translated pointers correspond to where the data
            #     is now really in memory.
            #
            # Note that 'curframe' contains non-translated pointers, and
            # of course the stack itself is full of non-translated pointers.
            #
            while True:
                callee = self.curframe
                #
                if not self.enumerating:
                    if not prev:
                        if not self.setup(obj):      # one-time initialization
                            return llmemory.NULL
                        prev = obj   # random value, but non-NULL
                    retaddraddr = self.translateptr(callee.frame_address)
                    retaddr = retaddraddr.address[0]
                    basewalker.locate_caller_based_on_retaddr(retaddr)
                    self.enumerating = True
                #
                # not really a loop, but kept this way for similarity
                # with asmgcroot:
                while True:
                    location = basewalker._shape_decompressor.next()
                    if location == 0:
                        break
                    addr = basewalker.getlocation(callee, location)
                    # yield the translated addr of the next GCREF in the stack
                    return self.translateptr(addr)
                #
                self.enumerating = False
                caller = self.otherframe
                reg = CALLEE_SAVED_REGS - 1
                while reg >= 0:
                    location = basewalker._shape_decompressor.next()
                    addr = basewalker.getlocation(callee, location)
                    caller.regs_stored_at[reg] = addr   # non-translated
                    reg -= 1

                location = basewalker._shape_decompressor.next()
                caller.frame_address = basewalker.getlocation(callee, location)
                # ^^^ non-translated
                if caller.frame_address == llmemory.NULL:
                    return self.teardown()    # completely done with this stack
                #
                self.otherframe = callee
                self.curframe = caller
                # loop back

        def translateptr(self, addr):
            return _tealet_rffi._tealet_translate_pointer(self.context, addr)

    _tealetrootwalker = TealetRootWalker()
    return _tealetrootwalker
get_tealetrootwalker._annspecialcase_ = 'specialize:memo'


def customtrace(obj, prev):
    tealetrootwalker = get_tealetrootwalker()
    return tealetrootwalker.next(obj, prev)

ASM_FRAMEDATA_HEAD_PTR = lltype.Ptr(lltype.FixedSizeArray(llmemory.Address, 2))
SUSPSTACK = lltype.GcStruct('SuspStack',
                            ('context', _tealet_rffi.TEALET_P),
                            ('anchor', ASM_FRAMEDATA_HEAD_PTR),
                            ('my_index', lltype.Signed),
                            ('next_unused', lltype.Signed),
                            rtti=True)
CUSTOMTRACEFUNC = lltype.FuncType([llmemory.Address, llmemory.Address],
                                  llmemory.Address)
customtraceptr = llhelper(lltype.Ptr(CUSTOMTRACEFUNC), customtrace)
lltype.attachRuntimeTypeInfo(SUSPSTACK, customtraceptr=customtraceptr)
NULL_SUSPSTACK = lltype.Ptr(SUSPSTACK)


class SuspendedStacks:

    def __init__(self):
        self.lst = []
        self.first_unused = -1

    def acquire(self):
        if self.first_unused == -1:
            p = lltype.malloc(SUSPSTACK)
            p.context = _tealet_rffi.NULL_TEALET
            p.my_index = len(self.lst)
            self.lst.append(p)
        else:
            p = self.lst[self.first_unused]
            self.first_unused = p.next_unused
        return p

    def release(self, p):
        p.next_unused = self.first_unused
        self.first_unused = p.my_index

suspendedstacks = SuspendedStacks()

def _stack_protected_call(callback):
    # :-/
    p = suspendedstacks.acquire()
    suspendedstacks.callback = callback
    anchor = lltype.malloc(ASM_FRAMEDATA_HEAD_PTR.TO, flavor='raw')
    anchor[0] = anchor[1] = llmemory.cast_ptr_to_adr(anchor)
    p.anchor = anchor
    r = pypy_asm_stackwalk2(callback, anchor)
    suspendedstacks.release(p)
    lltype.free(anchor, flavor='raw')
    return r

FUNCNOARG = lltype.FuncType([], rffi.INT)

pypy_asm_stackwalk2 = rffi.llexternal('pypy_asm_stackwalk',
                                      [lltype.Ptr(FUNCNOARG),
                                       ASM_FRAMEDATA_HEAD_PTR],
                                      rffi.INT, sandboxsafe=True,
                                      _nowrapper=True)

# ____________________________________________________________

Tealet, MainTealet = _make_classes(object)
