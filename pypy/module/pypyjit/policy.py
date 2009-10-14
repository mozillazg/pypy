from pypy.jit.metainterp.policy import JitPolicy

class PyPyJitPolicy(JitPolicy):

    def look_inside_pypy_module(self, modname):
        if mod.startswith('pypy.module.__builtin__'):
            if mod.endswith('operation') or mod.endswith('abstractinst'):
                return True

        modname, _ = modname.split('.', 1)
        if modname in ['pypyjit', 'signal', 'micronumpy', 'math']:
            return True
        return False

    def look_inside_function(self, func):
        mod = func.__module__ or '?'
        
        if mod.startswith('pypy.objspace.'):
            # gc_id operation
            if func.__name__ == 'id__ANY':
                return False
        if mod == 'pypy.rlib.rbigint':
            #if func.__name__ == '_bigint_true_divide':
            return False
        if mod == 'pypy.rpython.lltypesystem.module.ll_math':
            # XXX temporary, contains force_cast
            return False
        if '_geninterp_' in func.func_globals: # skip all geninterped stuff
            return False
        if mod.startswith('pypy.interpreter.astcompiler.'):
            return False
        if mod.startswith('pypy.interpreter.pyparser.'):
            return False
        if mod.startswith('pypy.module.'):
            modname = mod[len('pypy.'):]
            if not self.look_inside_pypy_module(modname):
                return False
            
        if mod.startswith('pypy.translator.'): # XXX wtf?
            return False
        # string builder interface
        if mod == 'pypy.rpython.lltypesystem.rbuilder':
            return False
        # rweakvaluedict implementation
        if mod == 'pypy.rlib.rweakrefimpl':
            return False
        
        return super(PyPyJitPolicy, self).look_inside_function(func)
