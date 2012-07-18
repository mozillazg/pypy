
from pypy.rlib.entrypoint import entrypoint
from pypy.rpython.lltypesystem import rffi, lltype
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.interpreter.error import OperationError

FUNCTIONS = {}

class Cache(object):
    def __init__(self, space):
        self.w_globals = space.newdict(module=True)
        space.call_method(self.w_globals, 'setdefault',
                          space.wrap('__builtins__'),
                          space.wrap(space.builtin))

def export_function(argtypes, restype):
    """ Export the function, sans the space argument
    """
    def wrapper(func):
        def newfunc(*args):
            llop.gc_stack_bottom(lltype.Void)   # marker for trackgcroot.py
            try:
                rffi.stackcounter.stacks_counter += 1
                res = func(*args)
            except Exception, e:
                print "Fatal error embedding API, cannot proceed"
                print str(e)
            rffi.stackcounter.stacks_counter -= 1
            return res
        FUNCTIONS[func.func_name] = (func, argtypes, restype)
        return func
    return wrapper

@export_function([rffi.CArrayPtr(rffi.CCHARP), rffi.CCHARP], lltype.Void)
def prepare_function(space, ll_names, ll_s):
    s = rffi.charp2str(ll_s)
    w_globals = space.fromcache(Cache).w_globals
    ec = space.getexecutioncontext()
    code_w = ec.compiler.compile(s, '<input>', 'exec', 0)
    code_w.exec_code(space, w_globals, w_globals)

@export_function([rffi.CCHARP, lltype.Signed, rffi.CArrayPtr(rffi.VOIDP)],
                 rffi.VOIDP)
def call_function(space, ll_name, numargs, ll_args):
    name = rffi.charp2str(ll_name)
    w_globals = space.fromcache(Cache).w_globals
    try:
        w_item = space.getitem(w_globals, space.wrap(name))
    except OperationError:
        print "Cannot find name %s" % name
        return lltype.nullptr(rffi.VOIDP.TO)
    args = [rffi.cast(lltype.Signed, ll_args[i]) for i in range(numargs)]
    try:
        w_res = space.call(w_item, space.newtuple([space.wrap(i) for i in args]))
    except OperationError:
        print "Error calling the function"
        return lltype.nullptr(rffi.VOIDP)
    try:
        res = space.int_w(w_res)
    except OperationError:
        print "Function did not return int"
        return lltype.nullptr(rffi.VOIDP)
    return res

def initialize(space):
    for name, (func, argtypes, restype) in FUNCTIONS.iteritems():
        def newfunc(*args):
            return func(space, *args)
        deco = entrypoint("embedding", argtypes, 'pypy_' + name, relax=True)
        deco(newfunc)
