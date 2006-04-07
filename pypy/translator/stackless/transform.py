from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython import rarithmetic, rclass
from pypy.translator.backendopt import support
from pypy.objspace.flow import model
from pypy.rpython.memory.gctransform import varoftype
from pypy.translator.unsimplify import copyvar
from pypy.annotation import model as annmodel
from pypy.rpython.annlowlevel import MixLevelHelperAnnotator
from pypy.translator.stackless import code 

STORAGE_TYPES = [llmemory.Address,
                 lltype.Signed,
                 lltype.Float,
                 lltype.SignedLongLong]
STORAGE_FIELDS = ['addr',
                  'long',
                  'float',
                  'longlong']

def storage_type(T):
    """Return the index into STORAGE_TYPES 
    """
    if T is lltype.Void:
        return None
    elif T is lltype.Float:
        return 2
    elif T in [lltype.SignedLongLong, lltype.UnsignedLongLong]:
        return 3
    elif T is llmemory.Address or isinstance(T, lltype.Ptr):
        return 0
    elif isinstance(T, lltype.Primitive):
        return 1
    else:
        raise Exception("don't know about %r" % (T,))



STATE_HEADER = lltype.Struct('state_header',
                             ('f_back', lltype.Ptr(lltype.ForwardReference())),
                             ('state', lltype.Signed))
STATE_HEADER.f_back.TO.become(STATE_HEADER)

null_state = lltype.nullptr(STATE_HEADER)
    
## def func(x):
##     return g() + x + 1

## STATE_func_0 = lltype.Struct('STATE_func_0',
##                              ('header', STATE_HEADER),
##                              ('saved_long_0', Signed))

## def func(x):
##     if global_state.top:
##         if global_state.restart_substate == 0:
##             frame = cast_pointer(lltype.Ptr(STATE_func_0), global_state.top)
##             x = frame.saved_long_0
##             retval = global_state.long_retval
##         else:
##             abort()
##     else:
##         try:
##             retval = g(x)
##         except UnwindException, u:
##             state = lltype.raw_malloc(STATE_func_0)
##             state.saved_long_0 = x
##             state.header.f_back = u.frame
##             state.header.state = XXX
##             u.frame = state.header
##             raise
        
##     return retval + x + 1


class StacklessTransfomer(object):
    def __init__(self, translator):
        self.translator = translator

        edata = translator.rtyper.getexceptiondata()
        self.frametypes = {}
        self.curr_graph = None
                
        mixlevelannotator = MixLevelHelperAnnotator(translator.rtyper)
        l2a = annmodel.lltype_to_annotation

        slp_main_loop_graph = mixlevelannotator.getgraph(
            code.slp_main_loop, [], l2a(lltype.Void))
        SLP_MAIN_LOOP_TYPE = lltype.FuncType([], lltype.Void)
        self.slp_main_loop_type_ptr = model.Constant(lltype.functionptr(
            SLP_MAIN_LOOP_TYPE, "slp_main_loop",
            graph=slp_main_loop_graph),
            SLP_MAIN_LOOP_TYPE)

        mixlevelannotator.finish()

    def frame_type_for_vars(self, vars):
        types = [storage_type(v.concretetype) for v in vars]
        counts = dict.fromkeys(range(len(STORAGE_TYPES)), 0)
        for t in types:
            counts[t] = counts[t] + 1
        keys = counts.keys()
        keys.sort()
        key = tuple([counts[k] for k in keys])
        if key in self.frametypes:
            return self.frametypes[key]
        else:
            fields = []
            for i, k in enumerate(key):
                for j in range(k):
                    fields.append(('state_%s_%d'%(STORAGE_FIELDS[i], j), STORAGE_TYPES[i]))
            T = lltype.Struct("state_%d_%d_%d_%d"%tuple(key),
                              ('header', STATE_HEADER),
                              *fields)
            self.frametypes[key] = T
            return T

    def transform_graph(self, graph):
        self.resume_points = []
        
        assert self.curr_graph is None
        self.curr_graph = graph
        
        for block in graph.iterblocks():
            self.transform_block(block)
        if self.resume_points:
            XXX

        self.curr_graph = None

    def transform_block(self, block):
        i = 0

        edata = self.translator.rtyper.getexceptiondata()
        etype = edata.lltype_of_exception_type
        evalue = edata.lltype_of_exception_value
        
        while i < len(block.operations):
            op = block.operations[i]
            if op.opname in ('direct_call', 'indirect_call'):
                after_block = support.split_block_with_keepalive(self.translator, self.curr_graph, block, i+1)
                link = block.exits[0]

                var_unwind_exception = varoftype(evalue)
                
                save_block = self.generate_save_block(link.args, var_unwind_exception)

                newlink = model.Link(link.args + [var_unwind_exception], 
                                     save_block, code.UnwindException)
                r_case = rclass.get_type_repr(self.translator.rtyper)
                newlink.llexitcase = r_case.convert_const(newlink.exitcase)
                block.exitswitch = model.c_last_exception
                block.recloseblock(link, newlink) # exits.append(newlink)
    # ARGH ... 

                block = after_block
                i = 0
            else:
                i += 1

    def generate_save_block(self, varstosave, var_unwind_exception):
        edata = self.translator.rtyper.getexceptiondata()
        etype = edata.lltype_of_exception_type
        evalue = edata.lltype_of_exception_value
        inputargs = [copyvar(self.translator, v) for v in varstosave]
        var_unwind_exception0 = copyvar(self.translator, var_unwind_exception)
        from pypy.rpython.rclass import getinstancerepr
        var_unwind_exception = varoftype(getinstancerepr(self.translator.rtyper,
            self.translator.annotator.bookkeeper.getuniqueclassdef(
                code.UnwindException)).lowleveltype)

        fields = []
        for i, v in enumerate(varstosave):
            if v.concretetype is not lltype.Void:
                fields.append(('field_%d'%(i,), v.concretetype))
        frame_type = lltype.Struct("S",
                            ('header', STATE_HEADER),
                            *fields)
        

        save_state_block = model.Block(inputargs + [var_unwind_exception])
        saveops = save_state_block.operations
        frame_state_var = varoftype(lltype.Ptr(frame_type))

        saveops.append(model.SpaceOperation('malloc',
                                        [model.Constant(frame_type, lltype.Void)],
                                        frame_state_var))
        
        saveops.extend(self.generate_saveops(frame_state_var, inputargs))

##             state.header.f_back = u.frame
##             state.header.state = XXX
##             u.frame = state.header
        header_var = varoftype(lltype.Ptr(STATE_HEADER))
        saveops.append(model.SpaceOperation("cast_pointer", [frame_state_var], header_var))
        var_unwind_exception_frame = varoftype(lltype.Ptr(STATE_HEADER))
        saveops.append(model.SpaceOperation("getfield",
                                            [var_unwind_exception, model.Constant("frame", lltype.Void)],
                                            var_unwind_exception_frame))
        saveops.append(model.SpaceOperation("setfield",
                                            [header_var, model.Constant("f_back", lltype.Void), var_unwind_exception_frame],
                                            varoftype(lltype.Void)))
        saveops.append(model.SpaceOperation("setfield",
                                            [var_unwind_exception, model.Constant("frame", lltype.Void)],
                                            varoftype(lltype.Void)))

        save_state_block.closeblock(model.Link([varoftype(etype), varoftype(evalue)],
                                               self.curr_graph.exceptblock))

        return save_state_block

        

    def generate_saveops(self, frame_state_var, varstosave):
        frame_type = frame_state_var.concretetype.TO
        ops = []
        for i, var in enumerate(varstosave):
            t = storage_type(var.concretetype)
            fname = model.Constant(frame_type._names[i+1], lltype.Void)
            ops.append(model.SpaceOperation('setfield',
                                            [frame_state_var, fname, var],
                                            varoftype(lltype.Void)))

        return ops
        
        
