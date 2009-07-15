"""
Generate AST node definitions from an ASDL description.
"""

import sys
import os
import asdl


class ASDLVisitor(asdl.VisitorBase):

    def __init__(self, stream):
        super(ASDLVisitor, self).__init__()
        self.stream = stream

    def visitModule(self, mod, *args):
        for df in mod.dfns:
            self.visit(df, *args)

    def visitSum(self, sum, *args):
        for tp in sum.types:
            self.visit(tp, *args)

    def visitType(self, tp, *args):
        self.visit(tp.value, *args)

    def visitProduct(self, prod, *args):
        for field in prod.fields:
            self.visit(field, *args)

    def visitConstructor(self, cons, *args):
        for field in cons.fields:
            self.visit(field, *args)

    def visitField(self, field):
        pass

    def emit(self, line, level=0):
        indent = "    "*level
        self.stream.write(indent + line + "\n")

    def is_simple_sum(self, sum):
        assert isinstance(sum, asdl.Sum)
        for constructor in sum.types:
            if constructor.fields:
                return False
        return True


class ASTNodeVisitor(ASDLVisitor):

    def visitType(self, tp):
        self.visit(tp.value, tp.name)

    def visitSum(self, sum, base):
        if self.is_simple_sum(sum):
            for i, cons in enumerate(sum.types):
                self.emit("%s = %i" % (cons.name, i + 1))
            self.emit("")
        else:
            self.emit("class %s(AST):" % (base,))
            self.emit("pass", 1)
            self.emit("")
            for cons in sum.types:
                self.visit(cons, base, sum.attributes)
                self.emit("")

    def visitProduct(self, product, name):
        self.emit("class %s(AST):" % (name,))
        self.emit("")
        self.make_constructor(product.fields)
        self.emit("")
        self.emit("def walkabout(self, visitor):", 1)
        self.emit("visitor.visit_%s(self)" % (name,), 2)
        self.emit("")

    def make_constructor(self, fields):
        if fields:
            args = ", ".join(str(field.name) for field in fields)
            self.emit("def __init__(self, %s):" % args, 1)
            for field in fields:
                self.visit(field)
        else:
            self.emit("def __init__(self):", 1)
            self.emit("pass", 2)

    def visitConstructor(self, cons, base, extra_attributes):
        self.emit("class %s(%s):" % (cons.name, base))
        self.emit("")
        self.make_constructor(cons.fields + extra_attributes)
        self.emit("")
        self.emit("def walkabout(self, visitor):", 1)
        self.emit("visitor.visit_%s(self)" % (cons.name,), 2)

    def visitField(self, field):
        self.emit("self.%s = %s" % (field.name, field.name), 2)


class ASTVisitorVisitor(ASDLVisitor):
    """A meta visitor! :)"""

    def visitModule(self, mod):
        self.emit("class ASTVisitor(object):")
        self.emit("")
        self.emit("def visit_sequence(self, seq):", 1)
        self.emit("for node in seq:", 2)
        self.emit("node.walkabout(self)", 3)
        self.emit("")
        self.emit("def default_visitor(self, node):", 1)
        self.emit("raise NodeVisitorNotImplemented", 2)
        self.emit("")
        super(ASTVisitorVisitor, self).visitModule(mod)
        self.emit("")

    def visitType(self, tp):
        if not (isinstance(tp.value, asdl.Sum) and
                self.is_simple_sum(tp.value)):
            super(ASTVisitorVisitor, self).visitType(tp, tp.name)

    def visitProduct(self, prod, name):
        self.emit("def visit_%s(self, node):" % (name,), 1)
        self.emit("self.default_visitor(node)", 2)

    def visitConstructor(self, cons, _):
        self.emit("def visit_%s(self, node):" % (cons.name,), 1)
        self.emit("self.default_visitor(node)", 2)


class GenericASTVisitorVisitor(ASDLVisitor):

    def visitModule(self, mod):
        self.emit("class GenericASTVisitor(ASTVisitor):")
        self.emit("")
        simple = set()
        for tp in mod.dfns:
            if isinstance(tp.value, asdl.Sum) and self.is_simple_sum(tp.value):
                simple.add(tp.name.value)
        super(GenericASTVisitorVisitor, self).visitModule(mod, simple)
        self.emit("")

    def visitType(self, tp, simple):
        if not (isinstance(tp.value, asdl.Sum) and
                self.is_simple_sum(tp.value)):
            super(GenericASTVisitorVisitor, self).visitType(tp, tp.name, simple)

    def visitProduct(self, prod, name, simple):
        self.make_visitor(name, prod.fields, simple)

    def visitConstructor(self, cons, _, simple):
        self.make_visitor(cons.name, cons.fields, simple)

    def make_visitor(self, name, fields, simple):
        self.emit("def visit_%s(self, node):" % (name,), 1)
        have_body = False
        for field in fields:
            if self.visitField(field, simple):
                have_body = True
        if not have_body:
            self.emit("pass", 2)
        self.emit("")

    def visitField(self, field, simple):
        if field.type.value not in asdl.builtin_types and \
                field.type.value not in simple:
            if field.seq or field.opt:
                self.emit("if node.%s:" % (field.name,), 2)
                level = 3
            else:
                level = 2
            if field.seq:
                template = "self.visit_sequence(node.%s)"
            else:
                template = "node.%s.walkabout(self)"
            self.emit(template % (field.name,), level)
            return True
        return False


HEAD = """# Generated by tools/asdl_py.py
from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter import typedef

class AST(Wrappable):

    def walkabout(self, visitor):
        raise AssertionError("walkabout() implementation not provided")

class NodeVisitorNotImplemented(Exception):
    pass

"""

visitors = [ASTNodeVisitor, ASTVisitorVisitor, GenericASTVisitorVisitor]


def main(argv):
    if len(argv) == 3:
        def_file, out_file = argv[1:]
    elif len(argv) == 1:
        print "Assuming default values of Python.asdl and ast.py"
        here = os.path.dirname(__file__)
        def_file = os.path.join(here, "Python.asdl")
        out_file = os.path.join(here, "..", "ast2.py")
    else:
        print >> sys.stderr, "invalid arguments"
        return 2
    mod = asdl.parse(def_file)
    fp = open(out_file, "w")
    try:
        fp.write(HEAD)
        for visitor in visitors:
            visitor(fp).visit(mod)
    finally:
        fp.close()


if __name__ == "__main__":
    sys.exit(main(sys.argv))
