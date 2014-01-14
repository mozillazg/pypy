

class JitDriverStaticData(object):
    """There is one instance of this class per JitDriver used in the program.
    """
    virtualizable_info = None
    greenfield_info = None
    
    def __init__(self, jitdriver, portal_graph, result_type):
        self.jitdriver = jitdriver
        self.portal_graph = portal_graph
        self.result_type = result_type
        self.num_green_args = len(jitdriver.greens)
        self.num_red_args = len(jitdriver.reds)
    
    # This is just a container with the following attributes (... set by):
    #    self.portal_runner_ptr ... rpython.jit.metainterp.warmspot
    #    self.portal_runner_adr ... rpython.jit.metainterp.warmspot
    #    self.portal_calldescr  ... rpython.jit.metainterp.warmspot
    #    self.red_args_types    ... rpython.jit.metainterp.warmspot
    #    self.virtualizable_info... rpython.jit.metainterp.warmspot
    #    self.greenfield_info   ... rpython.jit.metainterp.warmspot
    #    self.warmstate         ... rpython.jit.metainterp.warmspot
    #    self.handle_jitexc_from_bh rpython.jit.metainterp.warmspot
    #    self.no_loop_header    ... rpython.jit.metainterp.warmspot
    #    self.portal_finishtoken... rpython.jit.metainterp.pyjitpl
    #    self.propagate_exc_descr.. rpython.jit.metainterp.pyjitpl
    #    self.index             ... rpython.jit.codewriter.call
    #    self.mainjitcode       ... rpython.jit.codewriter.call

    # These attributes are read by the backend in CALL_ASSEMBLER:
    #    self.assembler_helper_adr
    #    self.index_of_virtualizable
    #    self.vable_token_descr
    #    self.portal_calldescr

    # warmspot sets extra attributes starting with '_' for its own use.

    def _freeze_(self):
        return True
