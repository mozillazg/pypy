"""this one logs simple assignments and somewhat clearly shows
that we need a nice API to define "joinpoints". Maybe a SAX-like
(i.e. event-based) API ?

XXX: crashes on everything else than simple assignment (AssAttr, etc.)
"""

from parser import ASTPrintnl, ASTConst, ASTName
from parser import install_compiler_hook

class Tracer:
    def visitModule(self, module):
        module.node = module.node.accept(self)
        return module 

    def default(self, node):
        for child in node.getChildNodes():
            # let's cheat a bit
            child.parent = node
            child.accept(self)
        return node 

    def visitAssign(self, assign):
        stmt = assign.parent
        varname = assign.nodes[0].name
        lognode = ASTPrintnl([ASTConst('%s <--' % varname), ASTName(varname)], None)
        index = stmt.nodes.index(assign)
        newstmts = stmt.nodes
        newstmts.insert(index + 1, lognode)
        stmt.nodes = newstmts
        return assign

    def __getattr__(self, attrname):
        if attrname.startswith('visit'):
            return self.default
        raise AttributeError('No such attribute: %s' % attrname)


def _trace(ast, enc):
    return ast.accept(Tracer())

install_compiler_hook(_trace)
