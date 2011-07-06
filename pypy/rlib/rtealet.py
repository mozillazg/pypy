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
        _gc_gcptr_array  = lltype.nullptr(GCPTR_ARRAY.TO)
        _gc_signed_array = lltype.nullptr(SIGNED_ARRAY.TO)

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

## XXX No support for multithreading so far!

class Switcher(object):
    current = None
    target = None
    exception = None
switcher = Switcher()

def _new(main, starting_tealet):
    switcher.current = main.current
    switcher.target = starting_tealet
    llmain = main.lltealet
    llrun = llhelper(_tealet_rffi.TEALET_RUN_P, _run)
    llarg = _tealet_rffi.NULL
    r = _new_critical(llmain, llrun, llarg)
    _check_exception(r)

def _new_critical(llmain, llrun, llarg):
    # critical function: no gc operation, and no gc variable alive!
    _save_shadow_stack()
    r = _tealet_rffi.tealet_new(llmain, llrun, llarg)
    _restore_shadow_stack()
    return r
_new_critical._dont_inline_ = True

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
    r = _switch_critical(target.lltealet)
    switcher.current = None
    switcher.target = None
    _check_exception(r)

def _switch_critical(lltarget):
    # critical code: no gc operation!
    _save_shadow_stack()
    r = _tealet_rffi.tealet_switch(lltarget)
    _restore_shadow_stack()
    return r
_switch_critical._dont_inline_ = True

def _check_exception(r):
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
# Shadow stack saving/restoring.

GCPTR_ARRAY  = lltype.Ptr(lltype.GcArray(llmemory.GCREF))
SIGNED_ARRAY = lltype.Ptr(lltype.GcArray(lltype.Signed))
WALKER_PTR   = lltype.Ptr(lltype.Struct('walker',
                                        ('gcptr_array', GCPTR_ARRAY),
                                        ('signed_array', SIGNED_ARRAY)))
walker = lltype.malloc(WALKER_PTR.TO, immortal=True)

def _save_shadow_stack():
    llop.gc_save_stack_roots(lltype.Void, walker)
    tealet = switcher.current
    ll_assert(not tealet._gc_gcptr_array, "tealet stack mismatch (save)")
    tealet._gc_gcptr_array  = walker.gcptr_array
    tealet._gc_signed_array = walker.signed_array
    walker.gcptr_array  = lltype.nullptr(GCPTR_ARRAY.TO)
    walker.signed_array = lltype.nullptr(SIGNED_ARRAY.TO)
_save_shadow_stack._dont_inline_ = True

def _restore_shadow_stack():
    tealet = switcher.target
    ll_assert(bool(tealet._gc_gcptr_array), "tealet stack mismatch (restore)")
    walker.gcptr_array  = tealet._gc_gcptr_array
    walker.signed_array = tealet._gc_signed_array
    tealet._gc_gcptr_array  = lltype.nullptr(GCPTR_ARRAY.TO)
    tealet._gc_signed_array = lltype.nullptr(SIGNED_ARRAY.TO)
    llop.gc_restore_stack_roots(lltype.Void, walker)
    walker.gcptr_array  = lltype.nullptr(GCPTR_ARRAY.TO)
    walker.signed_array = lltype.nullptr(SIGNED_ARRAY.TO)
_restore_shadow_stack._dont_inline_ = True

# ____________________________________________________________

Tealet, MainTealet = _make_classes(object)
