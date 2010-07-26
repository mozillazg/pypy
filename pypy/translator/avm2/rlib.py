
import inspect
import re

from mech.fusion.avm2.codegen import Argument
from mech.fusion.avm2 import constants

from pypy.rpython.ootypesystem import ootype
from pypy.objspace.flow import model as flowmodel
from pypy.translator.avm2.node import Node
from pypy.translator.avm2 import types_ as types

from types import MethodType

ESCAPE_FOR_REGEX = re.compile(r"([{}\(\)\^$&.\*\?\/\+\|\[\\\\]|\]|\-)")

class FunctionNode(Node):
    INSTANCE = None
    def render(self, generator):
        generator.begin_method(self.name, self.argspec, self.rettype)
        self.fn(self.cls, generator, *[Argument(name) for t, name in self.argspec])
        if self.rettype != constants.QName("void"):
            generator.return_value()
        generator.end_method()

def make_node(cls, fn, name, argtypes, rettype):
    if getattr(fn, "node", None):
        return fn.node
    fn.node = node = FunctionNode()
    node.cls = cls
    node.fn = fn
    node.name = name
    node.argspec = zip(argtypes, inspect.getargspec(fn).args[2:])
    node.rettype = rettype
    return node

def export(argtypes, rettype):
    def inner(fn):
        def inner_(cls, asm, *args):
            name = constants.packagedQName(cls.PACKAGE, fn.func_name)
            asm.db.pending_node(make_node(cls, fn, name, argtypes, rettype))
            asm.emit('findpropstrict', name)
            asm.load(*args)
            asm.emit('callproperty', name, len(args))
        return classmethod(inner_)
    return inner

class RString(object):
    WRAPPING = ootype.AbstractString
    PACKAGE  = "pypy.lib.str"

    @export(['String', 'String', 'int', 'int'], 'int')
    def ll_find(cls, asm, string, substr, start, end):
        asm.load(start, string)
        asm.get_field("length")
        asm.branch_if_greater_than("return -1")
        asm.load(string, 0, end)
        asm.call_method("slice", 2)
        asm.load(substr, start)
        asm.call_method("indexOf", 2)
        asm.return_value()
        asm.set_label("return -1")
        asm.load(-1)

    ll_find_char = ll_find

    @export(['String', 'String', 'int', 'int'], 'int')
    def ll_rfind(cls, asm, string, substr, start, end):
        asm.load(start, string)
        asm.get_field("length")
        asm.branch_if_greater_than("return -1")
        asm.load(string, start, end)
        asm.call_method("slice", 2)
        asm.load(substr)
        asm.call_method("lastIndexOf", 1)
        asm.dup()
        asm.load(-1)
        asm.branch_if_not_equal("return value")
        asm.pop()
        asm.set_label("return -1")
        asm.load(-1)
        asm.return_value()
        asm.set_label("return value")
        asm.load(start)
        asm.emit('add_i')
        asm.return_value()

    ll_rfind_char = ll_rfind

    @classmethod
    def escape_for_regex(cls, asm, string):
        if isinstance(string, flowmodel.Constant):
            asm.load(ESCAPE_FOR_REGEX.sub(r"\\\1", string.value))
        else:
            asm.emit('findpropstrict', constants.QName("RegExp"))
            asm.load(string, ESCAPE_FOR_REGEX.pattern, "g")
            asm.emit('constructprop', constants.QName("RegExp"), 2)
            asm.load(r"\$1")
            asm.call_method("replace", 2)

    @export(['String', 'String', 'int', 'int'], 'int')
    def ll_count(cls, asm, string, substr, start, end):
        asm.emit('findpropstrict', constants.QName("RegExp"))
        cls.escape_for_regex(substr)
        asm.load("g")
        asm.emit('constructprop', constants.QName("RegExp"), 2)
        asm.load(string, start, end)
        asm.call_method("slice", 2)
        asm.call_method("exec", 1)
        asm.get_field("length")

    ll_count_char = ll_count

    @export(['String', 'String'], 'Boolean')
    def ll_endswith(cls, asm, string, substr):
        asm.load(substr, string, substr, substr)
        asm.branch_if_false("rettrue")
        asm.get_field("length")
        asm.emit('negate_i')
        asm.call_method("slice", 1)
        asm.emit('equals')
        asm.return_value()
        asm.set_label("rettrue")
        asm.load(True)

    @export(['String', 'String'], 'Boolean')
    def ll_startswith(cls, asm, string, substr):
        asm.load(substr, string, 0, substr)
        asm.get_field("length")
        asm.call_method("slice", 2)
        asm.emit('equals')

RLib = {}

for cls in [RString]:
    for name in dir(cls):
        meth = getattr(cls, name)
        if isinstance(meth, MethodType):
            RLib[cls.WRAPPING.oopspec_name+'_'+name] = meth
