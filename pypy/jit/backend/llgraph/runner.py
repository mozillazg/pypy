
from weakref import WeakKeyDictionary

from pypy.jit.backend import model
from pypy.jit.metainterp.history import Const
from pypy.jit.metainterp.resoperation import rop
from pypy.rpython.llinterp import LLInterpreter

class LLLoop(object):
    def __init__(self, inputargs, operations):
        self.inputargs = inputargs
        self.operations = operations

class GuardFailed(Exception):
    def __init__(self, failargs, descr):
        self.failargs = failargs
        self.descr = descr

class ExecutionFinished(Exception):
    def __init__(self, descr, arg):
        self.descr = descr
        self.arg = arg

class Jump(Exception):
    def __init__(self, descr, args):
        self.descr = descr
        self.args = args

class LLGraphCPU(model.AbstractCPU):
    def __init__(self, rtyper):
        self.rtyper = rtyper
        self.llinterp = LLInterpreter(rtyper)
        self.known_labels = WeakKeyDictionary()

    def compile_loop(self, inputargs, operations, looptoken, log=True, name=''):
        self.total_compiled_loops += 1
        for i, op in enumerate(operations):
            if op.getopnum() == rop.LABEL:
                self.known_labels[op.getdescr()] = (operations, i)
        looptoken._llgraph_loop = LLLoop(inputargs, operations)

    def compile_bridge(self, faildescr, inputargs, operations,
                       original_loop_token):
        faildescr._llgraph_bridge = LLLoop(inputargs, operations)
        self.total_compiled_bridges += 1

    def make_execute_token(self, *argtypes):
        return self._execute_token

    def _execute_token(self, loop_token, *args):
        loop = loop_token._llgraph_loop
        frame = LLFrame(self, loop.inputargs, args)
        try:
            frame.execute(loop.operations)
            assert False
        except ExecutionFinished, e:
            self.latest_values = [e.arg]
            return e.descr
        except GuardFailed, e:
            self.latest_values = e.failargs
            return e.descr

    def get_latest_value_int(self, index):
        return self.latest_values[index]
    get_latest_value_float = get_latest_value_int

    def get_latest_value_count(self):
        return len(self.latest_values)

    def clear_latest_values(self, count):
        del self.latest_values

class LLFrame(object):
    def __init__(self, cpu, argboxes, args):
        self.env = {}
        self.cpu = cpu
        assert len(argboxes) == len(args)
        for box, arg in zip(argboxes, args):
            self.env[box] = arg

    def lookup(self, arg):
        if isinstance(arg, Const):
            return arg.value
        return self.env[arg]

    def execute(self, operations):
        i = 0
        while True:
            op = operations[i]
            args = [self.lookup(arg) for arg in op.getarglist()]
            self.current_op = op # for label
            try:
                resval = getattr(self, 'execute_' + op.getopname())(op.getdescr(),
                                                                    *args)
            except Jump, j:
                operations, i = self.cpu.known_labels[j.descr]
                label_op = operations[i]
                self.do_renaming(label_op.getarglist(), j.args)
                i += 1
                continue
            except GuardFailed, gf:
                if hasattr(gf.descr, '_llgraph_bridge'):
                    i = 0
                    bridge = gf.descr._llgraph_bridge
                    operations = bridge.operations
                    newargs = [self.env[arg] for arg in
                               self.current_op.getfailargs() if arg is not None]
                    self.do_renaming(bridge.inputargs, newargs)
                    continue
                raise
            if op.result is not None:
                assert resval is not None
                self.env[op.result] = resval
            else:
                assert resval is None
            i += 1

    def _getfailargs(self):
        r = []
        for arg in self.current_op.getfailargs():
            if arg is None:
                r.append(None)
            else:
                r.append(self.env[arg])
        return r

    def do_renaming(self, newargs, oldargs):
        assert len(newargs) == len(oldargs)
        newenv = {}
        for new, old in zip(newargs, oldargs):
            newenv[new] = old
        self.env = newenv

    # -----------------------------------------------------

    def fail_guard(self, descr):
        raise GuardFailed(self._getfailargs(), descr)

    def execute_finish(self, descr, arg=None):
        raise ExecutionFinished(descr, arg)

    def execute_label(self, descr, *args):
        argboxes = self.current_op.getarglist()
        self.do_renaming(argboxes, args)

    def execute_guard_true(self, descr, arg):
        if not arg:
            self.fail_guard(descr)

    def execute_guard_false(self, descr, arg):
        if arg:
            self.fail_guard(descr)    

    def execute_jump(self, descr, *args):
        raise Jump(descr, args)

def _setup():
    def _make_impl_from_blackhole_interp(opname):
        from pypy.jit.metainterp.blackhole import BlackholeInterpreter
        name = 'bhimpl_' + opname.lower()
        try:
            func = BlackholeInterpreter.__dict__[name]
        except KeyError:
            return
        for argtype in func.argtypes:
            if argtype not in ('i', 'r', 'f'):
                return
        #
        def _op_default_implementation(self, descr, *args):
            # for all operations implemented in the blackhole interpreter
            return func(*args)
        #
        _op_default_implementation.func_name = 'execute_' + opname
        return _op_default_implementation

    for k, v in rop.__dict__.iteritems():
        if not k.startswith("_"):
            func = _make_impl_from_blackhole_interp(k)
            if func is not None:
                setattr(LLFrame, 'execute_' + k.lower(), func)

_setup()
