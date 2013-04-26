
from rpython.translator.backendopt import graphanalyze
from rpython.rtyper.lltypesystem import lltype

class DestructorError(Exception):
    """The __del__() method contains unsupported operations.
    (You may have to use the newer rgc.register_finalizer())"""

class DestructorAnalyzer(graphanalyze.BoolGraphAnalyzer):
    """ Analyzer that checks if a destructor is lightweight enough for
    RPython.  The set of operations here is restrictive for a good reason
    - it's better to be safe. Specifically disallowed operations:

    * anything that escapes self
    * anything that can allocate
    """
    ok_operations = ['ptr_nonzero', 'ptr_iszero', 'ptr_eq', 'ptr_ne',
                     'free', 'same_as',
                     'direct_ptradd', 'force_cast', 'track_alloc_stop',
                     'raw_free']

    def check_destructor(self, graph):
        self.unsupported_op = None
        result = self.analyze_direct_call(graph)
        if result is self.top_result():
            raise DestructorError(DestructorError.__doc__, graph,
                                  self.unsupported_op)

    def analyze_simple_operation(self, op, graphinfo):
        if op.opname in self.ok_operations:
            return self.bottom_result()
        if (op.opname.startswith('int_') or op.opname.startswith('float_')
            or op.opname.startswith('cast_')):
            return self.bottom_result()
        if (op.opname == 'setfield' or op.opname == 'bare_setfield' or
            op.opname == 'setarrayitem' or op.opname == 'bare_setarrayitem'):
            TP = op.args[-1].concretetype
            if not isinstance(TP, lltype.Ptr) or TP.TO._gckind == 'raw':
                # primitive type
                return self.bottom_result()
        if op.opname == 'getfield' or op.opname == 'getarrayitem':
            TP = op.result.concretetype
            if not isinstance(TP, lltype.Ptr) or TP.TO._gckind == 'raw':
                # primitive type
                return self.bottom_result()
        self.unsupported_op = op
        return self.top_result()
