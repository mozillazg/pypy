"""
Symbol tabling building.
"""

from pypy.interpreter.astcompiler import ast2 as ast, misc
from pypy.interpreter.pyparser.error import SyntaxError

# These are for internal use only:
SYM_BLANK = 0
SYM_GLOBAL = 1
SYM_ASSIGNED = 2 # Or deleted actually.
SYM_PARAM = 2 << 1
SYM_USED = 2 << 2
SYM_BOUND = (SYM_PARAM | SYM_ASSIGNED)

# codegen.py actually deals with these:
SCOPE_UNKNOWN = 0
SCOPE_GLOBAL_IMPLICIT = 1
SCOPE_GLOBAL_EXPLICIT = 2
SCOPE_LOCAL = 3
SCOPE_FREE = 4
SCOPE_CELL = 5


class Scope(object):

    def __init__(self, node, name, optimized):
        self.node = node
        self.parent = None
        self.name = name
        self.optimized = optimized
        self.symbols = None
        self.roles = {}
        self.varnames = []
        self.children = []
        self.has_free = False
        self.child_has_free = False
        self.nested = False

    def lookup(self, name):
        return self.symbols.get(self.mangle(name), SCOPE_UNKNOWN)

    def note_symbol(self, identifier, role):
        mangled = self.mangle(identifier)
        new_role = role
        if identifier in self.roles:
            old_role = self.roles[identifier]
            if old_role & SYM_PARAM and role & SYM_PARAM:
                err = "duplicate argument '%s' in function definition" % \
                    (identifier,)
                raise SyntaxError(err, self.node.lineno, self.node.col_offset)
            new_role |= old_role
        self.roles[mangled] = new_role
        if role & SYM_PARAM:
            self.varnames.append(mangled)
        return mangled

    def note_yield(self, yield_node):
        raise SyntaxError("yield outside function", yield_node.lineno,
                          yield_node.col_offset)

    def note_return(self, ret):
        raise SyntaxError("return outside function", ret.lineno,
                          ret.col_offset)

    def note_exec(self, exc):
        pass

    def note_import_star(self, imp):
        pass

    def mangle(self, name):
        if self.parent:
            return self.parent.mangle(name)
        else:
            return name

    def add_child(self, child_scope):
        child_scope.parent = self
        self.children.append(child_scope)

    def _finalize_name(self, name, flags, local, bound, free, globs):
        if flags & SYM_GLOBAL:
            if flags & SYM_PARAM:
                raise SyntaxError("name %r is both local and global" % (name,),
                                  self.node.lineno, self.node.col_offset)
            self.symbols[name] = SCOPE_GLOBAL_EXPLICIT
            globs[name] = None
            if bound:
                try:
                    del bound[name]
                except KeyError:
                    pass
        elif flags & SYM_BOUND:
            self.symbols[name] = SCOPE_LOCAL
            local[name] = None
            try:
                del globs[name]
            except KeyError:
                pass
        elif bound and name in bound:
            self.symbols[name] = SCOPE_FREE
            free[name] = None
            self.has_free = True
        elif name in globs:
            self.symbols[name] = SCOPE_GLOBAL_IMPLICIT
        else:
            if self.nested:
                self.has_free = True
            self.symbols[name] = SCOPE_GLOBAL_IMPLICIT

    def _pass_on_bindings(self, local, bound, globs, new_bound, new_globs):
        new_globs.update(globs)
        if bound:
            new_bound.update(bound)

    def _finalize_cells(self, free):
        pass

    def _check_optimization(self):
        pass

    _hide_bound_from_nested_scopes = False

    def finalize(self, bound, free, globs):
        self.symbols = {}
        local = {}
        new_globs = {}
        new_bound = {}
        new_free = {}
        if self._hide_bound_from_nested_scopes:
            self._pass_on_bindings(local, bound, globs, new_bound, new_globs)
        for name, flags in self.roles.iteritems():
            self._finalize_name(name, flags, local, bound, free, globs)
        if not self._hide_bound_from_nested_scopes:
            self._pass_on_bindings(local, bound, globs, new_bound, new_globs)
        child_frees = {}
        for child in self.children:
            child_free = new_free.copy()
            child.finalize(new_bound.copy(), child_free, new_globs.copy())
            child_frees.update(child_free)
            if child.has_free or child.child_has_free:
                self.child_has_free = True
        new_free.update(child_frees)
        self._finalize_cells(new_free)
        for name in new_free:
            try:
                role_here = self.roles[name]
            except KeyError:
                if name in bound:
                    self.symbols[name] = SCOPE_FREE
            else:
                if role_here & (SYM_ASSIGNED | SYM_GLOBAL) and \
                        self._hide_bound_from_nested_scopes:
                    self.symbols[name] = SCOPE_FREE
        self._check_optimization()
        free.update(new_free)


class ModuleScope(Scope):

    def __init__(self, module):
        Scope.__init__(self, module, "top", False)


class FunctionScope(Scope):

    def __init__(self, func, name):
        Scope.__init__(self, func, name, True)
        self.has_variable_arg = False
        self.has_keywords_arg = False
        self.is_generator = False
        self.return_with_value = False
        self.import_star = None
        self.bare_exec = None

    def note_yield(self, yield_node):
        if self.return_with_value:
            raise SyntaxError("return with value in generator",
                              yield_node.lineno, yield_node.col_offset)
        self.is_generator = True

    def note_return(self, ret):
        if self.is_generator and ret.value:
            raise SyntaxError("return with value in generator", ret.lineno,
                              ret.col_offset)
        self.return_with_value = True

    def note_exec(self, exc):
        self.has_exec = True
        if not exc.globals:
            self.optimized = False
            self.bare_exec = exc

    def note_import_star(self, imp):
        self.optimized = False
        self.import_star = imp

    def note_variable_arg(self, vararg):
        self.has_variable_arg = True

    def note_keywords_arg(self, kwarg):
        self.has_keywords_arg = True

    def add_child(self, child_scope):
        Scope.add_child(self, child_scope)
        child_scope.nested = True

    def _pass_on_bindings(self, local, bound, globs, new_bound, new_globs):
        new_bound.update(local)
        Scope._pass_on_bindings(self, local, bound, globs, new_bound, new_globs)

    def _finalize_cells(self, free):
        for name, role in self.symbols.iteritems():
            if role == SCOPE_LOCAL and name in free:
                self.symbols[name] = SCOPE_CELL
                del free[name]

    def _check_optimization(self):
        if (self.has_free or self.child_has_free) and not self.optimized:
            err = None
            if self.import_star:
                node = self.import_star
                if self.bare_exec:
                    err = "function %r uses import * and bare exec, " \
                        "which are illegal because it %s"
                else:
                    err = "import * is not allowed in function %r because it %s"
            elif self.bare_exec:
                node = self.bare_exec
                err = "unqualified exec is not allowed in function %r " \
                    "because it %s"
            else:
                raise AssertionError("unkown reason for unoptimization")
            if self.child_has_free:
                trailer = "contains a nested function with free variables"
            else:
                trailer = "is a nested function"
            raise SyntaxError(err % (self.name, trailer), node.lineno,
                              node.col_offset)


class ClassScope(Scope):

    _hide_bound_from_nested_scopes = True

    def __init__(self, clsdef):
        Scope.__init__(self, clsdef, clsdef.name, False)

    def mangle(self, name):
        return misc.mangle(name, self.name)


class SymtableBuilder(ast.GenericASTVisitor):

    def __init__(self, space, module):
        self.space = space
        self.module = module
        self.scopes = {}
        self.scope = None
        self.stack = []
        self.tmp_name_counter = 0
        top = ModuleScope(module)
        self.globs = top.roles
        self.push_scope(top)
        module.walkabout(self)
        top.finalize(None, {}, {})
        self.pop_scope()
        assert not self.stack

    def push_scope(self, scope):
        if self.stack:
            self.stack[-1].add_child(scope)
        self.stack.append(scope)
        self.scopes[scope.node] = scope
        # Convenience
        self.scope = scope

    def pop_scope(self):
        self.stack.pop()
        if self.stack:
            self.scope = self.stack[-1]
        else:
            self.scope = None

    def find_scope(self, scope_node):
        return self.scopes[scope_node]

    def implicit_arg(self, pos):
        name = ".%i" % (pos,)
        self.note_symbol(name, SYM_PARAM)

    def new_temporary_name(self):
        self.note_symbol("_[%i]" % (self.tmp_name_counter,), SYM_ASSIGNED)
        self.tmp_name_counter += 1

    def note_symbol(self, identifier, role):
        mangled = self.scope.note_symbol(identifier, role)
        if role & SYM_GLOBAL:
            if identifier in self.globs:
                role |= self.globs[mangled]
            self.globs[mangled] = role

    def visit_FunctionDef(self, func):
        self.note_symbol(func.name, SYM_ASSIGNED)
        if func.args.defaults:
            self.visit_sequence(func.args.defaults)
        if func.decorators:
            self.visit_sequence(func.decorators)
        self.push_scope(FunctionScope(func, func.name))
        func.args.walkabout(self)
        self.visit_sequence(func.body)
        self.pop_scope()

    def visit_Return(self, ret):
        self.scope.note_return(ret)
        ast.GenericASTVisitor.visit_Return(self, ret)

    def visit_ClassDef(self, clsdef):
        self.note_symbol(clsdef.name, SYM_ASSIGNED)
        if clsdef.bases:
            self.visit_sequence(clsdef.bases)
        self.push_scope(ClassScope(clsdef))
        self.visit_sequence(clsdef.body)
        self.pop_scope()

    def visit_ImportFrom(self, imp):
        for alias in imp.names:
            if self.visit_alias(alias):
                self.scope.note_import_star(imp)

    def visit_alias(self, alias):
        if alias.asname:
            store_name = alias.asname
        else:
            store_name = alias.name
            if store_name == "*":
                return True
            dot = store_name.find(".")
            if dot != -1:
                store_name = store_name[:dot]
        self.note_symbol(store_name, SYM_ASSIGNED)
        return False

    def visit_Exec(self, exc):
        self.scope.note_exec(exc)
        ast.GenericASTVisitor.visit_Exec(self, exc)

    def visit_Yield(self, yie):
        self.scope.note_yield(yie)
        ast.GenericASTVisitor.visit_Yield(self, yie)

    def visit_Global(self, glob):
        for name in glob.names:
            self.note_symbol(name, SYM_GLOBAL)

    def visit_Lambda(self, lamb):
        if lamb.args.defaults:
            self.visit_sequence(lamb.defaults)
        self.push_scope(FunctionScope(lamb, "lambda"))
        lamb.args.walkabout(self)
        lamb.body.walkabout(self)
        self.pop_scope()

    def visit_GeneratorExp(self, genexp):
        outer = genexp.generators[0]
        outer.iter.walkabout(self)
        self.push_scope(FunctionScope(genexp, "genexp"))
        self.implicit_arg(0)
        outer.target.walkabout(self)
        if outer.ifs:
            self.visit_sequence(outer.ifs)
        self.visit_sequence(genexp.generators[1:])
        genexp.elt.walkabout(self)
        self.pop_scope()

    def visit_ListComp(self, lc):
        self.new_temporary_name()
        ast.GenericASTVisitor.visit_ListComp(self, lc)

    def visit_arguments(self, arguments):
        assert isinstance(self.scope, FunctionScope) # Annotator hint.
        if arguments.args:
            self._handle_params(arguments.args, True)
        if arguments.vararg:
            self.note_symbol(arguments.vararg, SYM_PARAM)
            self.scope.note_variable_arg(arguments.vararg)
        if arguments.kwarg:
            self.note_symbol(arguments.kwarg, SYM_PARAM)
            self.scope.note_keywords_arg(arguments.kwarg)
        if arguments.args:
            self._handle_nested_params(arguments.args)

    def _handle_params(self, params, is_toplevel):
        for i in range(len(params)):
            arg = params[i]
            if isinstance(arg, ast.Name):
                self.note_symbol(arg.id, SYM_PARAM)
            elif isinstance(arg, ast.Tuple):
                if is_toplevel:
                    self.implicit_arg(i)
            else:
                raise AssertionError("unkown parameter type")
        if not is_toplevel:
            self._handle_nested_params(params)

    def _handle_nested_params(self, params):
        for param in params:
            if isinstance(param, ast.Tuple):
                self._handle_params(param.elts, False)

    def visit_Name(self, name):
        if name.ctx == ast.Load:
            role = SYM_USED
        else:
            role = SYM_ASSIGNED
        self.note_symbol(name.id, role)
