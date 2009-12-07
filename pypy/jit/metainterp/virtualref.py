from pypy.rpython.rmodel import inputconst, log
from pypy.rpython.lltypesystem import lltype, llmemory, rffi, rclass
from pypy.rlib.objectmodel import specialize
from pypy.jit.metainterp import history


def replace_force_virtual_with_call(warmrunnerdesc, graphs):
    # similar to rvirtualizable2.replace_force_virtualizable_with_call().
    c_funcptr = None
    count = 0
    for graph in graphs:
        for block in graph.iterblocks():
            for op in block.operations:
                if op.opname == 'jit_force_virtual':
                    # first compute c_funcptr, but only if there is any
                    # 'jit_force_virtual' around
                    if c_funcptr is None:
                        c_funcptr = get_force_virtual_fnptr(warmrunnerdesc)
                    #
                    op.opname = 'direct_call'
                    op.args = [c_funcptr, op.args[0]]
                    count += 1
    if c_funcptr is not None:
        log("replaced %d 'jit_force_virtual' with %r" % (count,
                                                         c_funcptr.value))
    #
    # record the type JIT_VIRTUAL_REF explicitly in the rtyper, too
    warmrunnerdesc.rtyper.set_type_for_typeptr(jit_virtual_ref_vtable,
                                               JIT_VIRTUAL_REF)

# ____________________________________________________________


# we make the low-level type of an RPython class directly
JIT_VIRTUAL_REF = lltype.GcStruct('JitVirtualRef',
                                  ('super', rclass.OBJECT),
                                  ('virtual_token', lltype.Signed),
                                  ('virtualref_index', lltype.Signed),
                                  ('forced', rclass.OBJECTPTR))
jit_virtual_ref_vtable = lltype.malloc(rclass.OBJECT_VTABLE, zero=True,
                                       flavor='raw')
jit_virtual_ref_vtable.name = rclass.alloc_array_name('jit_virtual_ref')

# The 'virtual_token' field has the same meaning as the 'vable_token' field
# of a virtualizable.  It is equal to:
#   * 0 (TOKEN_NONE) when tracing, except as described below;
#   * -1 (TOKEN_TRACING_RESCALL) during tracing when we do a residual call;
#   * addr in the CPU stack (set by FORCE_TOKEN) when running the assembler;
#   * 0 (TOKEN_NONE) after the virtual is forced, if it is forced at all.
TOKEN_NONE            = 0
TOKEN_TRACING_RESCALL = -1

@specialize.memo()
def get_jit_virtual_ref_const_class(cpu):
    adr = llmemory.cast_ptr_to_adr(jit_virtual_ref_vtable)
    return history.ConstAddr(adr, cpu)

@specialize.memo()
def get_descr_virtual_token(cpu):
    return cpu.fielddescrof(JIT_VIRTUAL_REF, 'virtual_token')

@specialize.memo()
def get_descr_virtualref_index(cpu):
    return cpu.fielddescrof(JIT_VIRTUAL_REF, 'virtualref_index')

@specialize.memo()
def get_descr_forced(cpu):
    return cpu.fielddescrof(JIT_VIRTUAL_REF, 'forced')

def virtual_ref_during_tracing(real_object):
    assert real_object
    vref = lltype.malloc(JIT_VIRTUAL_REF)
    p = lltype.cast_pointer(rclass.OBJECTPTR, vref)
    p.typeptr = jit_virtual_ref_vtable
    vref.virtual_token = TOKEN_NONE
    vref.forced = lltype.cast_opaque_ptr(rclass.OBJECTPTR, real_object)
    return lltype.cast_opaque_ptr(llmemory.GCREF, vref)

def tracing_before_residual_call(gcref):
    vref = lltype.cast_opaque_ptr(lltype.Ptr(JIT_VIRTUAL_REF), gcref)
    assert not vref.virtual_token
    vref.virtual_token = TOKEN_TRACING_RESCALL

def tracing_after_residual_call(gcref):
    vref = lltype.cast_opaque_ptr(lltype.Ptr(JIT_VIRTUAL_REF), gcref)
    if vref.virtual_token:
        # not modified by the residual call; assert that it is still
        # set to TOKEN_TRACING_RESCALL and clear it.
        assert vref.virtual_token == TOKEN_TRACING_RESCALL
        vref.virtual_token = TOKEN_NONE
        return False
    else:
        # marker "modified during residual call" set.
        return True

def forced_single_vref(gcref, real_object):
    assert real_object
    vref = lltype.cast_opaque_ptr(lltype.Ptr(JIT_VIRTUAL_REF), gcref)
    assert (vref.virtual_token != TOKEN_NONE and
            vref.virtual_token != TOKEN_TRACING_RESCALL)
    vref.virtual_token = TOKEN_NONE
    vref.forced = lltype.cast_opaque_ptr(rclass.OBJECTPTR, real_object)

def continue_tracing(gcref, real_object):
    vref = lltype.cast_opaque_ptr(lltype.Ptr(JIT_VIRTUAL_REF), gcref)
    assert vref.virtual_token != TOKEN_TRACING_RESCALL
    vref.virtual_token = TOKEN_NONE
    vref.forced = lltype.cast_opaque_ptr(rclass.OBJECTPTR, real_object)

# ____________________________________________________________

def get_force_virtual_fnptr(warmrunnerdesc):
    cpu = warmrunnerdesc.cpu
    #
    def force_virtual_if_necessary(inst):
        if not inst or inst.typeptr != jit_virtual_ref_vtable:
            return inst    # common, fast case
        return force_virtual(cpu, inst)
    #
    FUNC = lltype.FuncType([rclass.OBJECTPTR], rclass.OBJECTPTR)
    funcptr = warmrunnerdesc.helper_func(
        lltype.Ptr(FUNC),
        force_virtual_if_necessary)
    return inputconst(lltype.typeOf(funcptr), funcptr)

def force_virtual(cpu, inst):
    vref = lltype.cast_pointer(lltype.Ptr(JIT_VIRTUAL_REF), inst)
    token = vref.virtual_token
    if token != TOKEN_NONE:
        if token == TOKEN_TRACING_RESCALL:
            # The "virtual" is not a virtual at all during tracing.
            # We only need to reset virtual_token to TOKEN_NONE
            # as a marker for the tracing, to tell it that this
            # "virtual" escapes.
            vref.virtual_token = TOKEN_NONE
        else:
            assert not vref.forced
            from pypy.jit.metainterp.compile import ResumeGuardForcedDescr
            ResumeGuardForcedDescr.force_now(cpu, token)
            assert vref.virtual_token == TOKEN_NONE
    assert vref.forced
    return vref.forced
force_virtual._dont_inline_ = True
