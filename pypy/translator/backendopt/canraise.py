from pypy.translator.simplify import get_graph
from pypy.rpython.lltypesystem.lloperation import llop, LL_OPERATIONS
from pypy.rpython.lltypesystem import lltype
from pypy.translator.backendopt import graphanalyze
from pypy.translator.simplify import get_funcobj

import py
from pypy.tool.ansi_print import ansi_log
log = py.log.Producer("canraise") 
py.log.setconsumer("canraise", ansi_log) 

class RaiseAnalyzer(graphanalyze.BoolGraphAnalyzer):
    def analyze_simple_operation(self, op, graphinfo):
        try:
            if LL_OPERATIONS[op.opname].canraise:
                self.reason = op
                return True
            return False
        except KeyError:
            log.WARNING("Unknown operation: %s" % op.opname)
            self.reason = op
            return True

    def analyze_external_call(self, op, seen=None):
        fnobj = get_funcobj(op.args[0].value)
        if getattr(fnobj, 'canraise', True):
            self.reason = 'external call:', fnobj
            return True
        return False

    def analyze_external_method(self, op, TYPE, meth):
        assert op.opname == 'oosend'
        if getattr(meth, '_can_raise', True):
            self.reason = 'external method:', meth
            return True
        return False

    def analyze_exceptblock(self, block, seen=None):
        self.reason = "except block:", block
        return True

    # backward compatible interface
    def can_raise(self, op, seen=None):
        return self.analyze(op, seen)
