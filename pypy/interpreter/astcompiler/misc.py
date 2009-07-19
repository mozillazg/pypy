from pypy.interpreter import gateway
from pypy.interpreter.astcompiler import ast2 as ast
from pypy.rlib.objectmodel import we_are_translated
from pypy.rlib.unroll import unrolling_iterable


app = gateway.applevel("""
def syntax_warning(msg, fn, lineno, offset):
    import warnings
    try:
        warnings.warn_explicit(msg, SyntaxWarning, fn, lineno)
    except SyntaxWarning:
        raise SyntaxError(msg, fn, lineno, offset)
""", filename=__file__)
_emit_syntax_warning = app.interphook("syntax_warning")
del app

def syntax_warning(space, msg, fn, lineno, offset):
    w_msg = space.wrap(msg)
    w_filename = space.wrap(fn)
    w_lineno = space.wrap(lineno)
    w_offset = space.wrap(offset)
    _emit_syntax_warning(space, w_msg, w_filename, w_lineno, w_offset)


CONST_NOT_CONST = -1
CONST_FALSE = 0
CONST_TRUE = 1

def expr_constant(space, expr):
    if isinstance(expr, ast.Num):
        return int(space.is_true(expr.n))
    elif isinstance(expr, ast.Str):
        return int(space.is_true(expr.s))
    return CONST_NOT_CONST

def is_constant(expr):
    if isinstance(expr, (ast.Num, ast.Str)):
        return True
    return False


def dict_to_switch(d):
    def lookup(query):
        if we_are_translated():
            for key, value in unrolling_iteritems:
                if key == query:
                    return value
            else:
                raise KeyError
        else:
            return d[query]
    lookup._always_inline_ = True
    unrolling_iteritems = unrolling_iterable(d.iteritems())
    return lookup


def flatten(tup):
    elts = []
    for elt in tup:
        if type(elt) == tuple:
            elts = elts + flatten(elt)
        else:
            elts.append(elt)
    return elts

class Counter:
    def __init__(self, initial):
        self.count = initial

    def next(self):
        i = self.count
        self.count += 1
        return i

MANGLE_LEN = 256 # magic constant from compile.c

def mangle(name, klass):
    if not name.startswith('__'):
        return name
    if len(name) + 2 >= MANGLE_LEN:
        return name
    if name.endswith('__'):
        return name
    try:
        i = 0
        while klass[i] == '_':
            i = i + 1
    except IndexError:
        return name
    klass = klass[i:]

    tlen = len(klass) + len(name)
    if tlen > MANGLE_LEN:
        end = len(klass) + MANGLE_LEN-tlen
        if end < 0:
            klass = ''     # slices of negative length are invalid in RPython
        else:
            klass = klass[:end]

    return "_%s%s" % (klass, name)

class Queue(object):
    def __init__(self, item):
        self.head = [item]
        self.tail = []

    def pop(self):
        if self.head:
            return self.head.pop()
        else:
            for i in range(len(self.tail)-1, -1, -1):
                self.head.append(self.tail[i])
            self.tail = []
            return self.head.pop()

    def extend(self, items):
        self.tail.extend(items)

    def nonempty(self):
        return self.tail or self.head

def set_filename(filename, tree):
    """Set the filename attribute to filename on every node in tree"""
    worklist = Queue(tree)
    while worklist.nonempty():
        node = worklist.pop()
        assert isinstance(node, ast.Node)
        node.filename = filename
        worklist.extend(node.getChildNodes())
