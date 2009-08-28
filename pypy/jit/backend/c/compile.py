from pypy.rpython.lltypesystem import lltype, rffi
from pypy.tool.udir import udir
from pypy.rlib import libffi
from pypy.rlib.objectmodel import we_are_translated
from pypy.jit.metainterp import resoperation
from pypy.jit.metainterp.resoperation import rop
import os


class Compiler:
    FUNCPTR = lltype.Ptr(lltype.FuncType([], rffi.INT))
    
    def __init__(self):
        self.fn_counter = 0
        self.filename_counter = 0
        self.c_jit_al = None
        self.c_jit_ap = None
        self.guard_operations = []

    def run(self, loop):
        res = loop._c_jit_func()
        res = rffi.cast(lltype.Signed, res)
        return self.guard_operations[res]

    def compile_operations(self, loop, guard_op=None):
        if guard_op is None:
            loop._c_jit_counter = self.fn_counter
            if loop.operations[-1].opnum == rop.JUMP:
                simpleloop = loop.operations[-1].jump_target is loop
            else:
                simpleloop = False
            fn, funcname = self.write(loop.inputargs,
                                      loop.operations, simpleloop)
        else:
            fn, _ = self.write(guard_op.inputargs,
                               guard_op.suboperations, False)
            funcname = None
        sofn = self.compile_file(fn)
        self.load_file(sofn, loop, funcname)

    def get_next_filename(self):
        fn = '_c_jit%s.i' % self.filename_counter
        self.filename_counter += 1
        return str(udir.ensure('c_jit', dir=1).join(fn))

    def write(self, inputargs, operations, simpleloop):
        fn = self.get_next_filename()
        f = open(fn, 'w')
        notfirst = self.c_jit_al is not None
        print >> f, '%slong _c_jit_al[1000];' % ('extern ' * notfirst)
        print >> f, '%svoid*_c_jit_ap[1000];' % ('extern ' * notfirst)
        if operations[-1].opnum == rop.JUMP and not simpleloop:
            print >> f, 'extern int _c_jit_f%d(void);' % (
                operations[-1].jump_target._c_jit_counter)
        self.simpleloop = simpleloop
        #
        guard_counter = self.fn_counter + 1
        for op in operations:
            if op.is_guard():
                assert op.suboperations[0].opnum == rop.FAIL
                op.inputargs = op.suboperations[0].args
                print >> f, 'int _c_jit_f%d()__attribute__((weak));' % (
                    guard_counter)
                print >> f, 'int _c_jit_f%d(){return %d;}' % (
                    guard_counter, guard_counter)
                self.set_guard_operation(op.suboperations[0], guard_counter)
                guard_counter += 1
        #
        funcname = '_c_jit_f%d' % self.fn_counter
        print >> f, 'int %s(){' % funcname
        self.argnum = {}
        j = 0
        for arg in inputargs:
            self.argnum[arg] = j
            print >> f, 'long v%d=_c_jit_al[%d];' % (j, j)
            j += 1
        if simpleloop:
            print >> f, 'while(1){'
        for op in operations:
            meth = getattr(self, 'generate_' + resoperation.opname[op.opnum])
            meth(f, op)
        print >> f, '}'
        #
        f.close()
        self.fn_counter = guard_counter
        return fn, funcname

    def compile_file(self, fn):
        import subprocess
        basename = os.path.basename(fn)
        output_fn = basename[:-2]+'.so'
        retcode = subprocess.call(
            ['gcc', basename, '-shared', '-o', output_fn],
            cwd=os.path.dirname(fn))
        if retcode != 0:
            raise CompilerError(fn)
        return os.path.join(os.path.dirname(fn), output_fn)

    def load_file(self, fn, loop, funcname):
        handle = libffi.dlopen(fn, libffi.RTLD_GLOBAL | libffi.RTLD_NOW)
        if self.c_jit_al is None:
            c_jit_al = libffi.dlsym(handle, "_c_jit_al")
            self.c_jit_al = rffi.cast(rffi.LONGP, c_jit_al)
        if funcname is not None:
            c_func = libffi.dlsym(handle, funcname)
            loop._c_jit_func = rffi.cast(self.FUNCPTR, c_func)

    def set_guard_operation(self, op, counter):
        while len(self.guard_operations) <= counter:
            self.guard_operations.append(None)
        self.guard_operations[counter] = op

    # ____________________________________________________________

    def _binary(expr):
        def generate_binary(self, f, op):
            argnum = self.argnum
            argnum[op.result] = j = len(argnum)
            expr2 = expr % (argnum[op.args[0]], argnum[op.args[1]])
            print >> f, 'long v%d=%s;' % (j, expr2)
        return generate_binary

    generate_INT_LT = _binary('v%d<v%d')
    generate_INT_LE = _binary('v%d<=v%d')
    generate_INT_EQ = _binary('v%d==v%d')
    generate_INT_NE = _binary('v%d!=v%d')
    generate_INT_GT = _binary('v%d>v%d')
    generate_INT_GE = _binary('v%d>=v%d')

    generate_UINT_LT = _binary('((unsigned long)v%d)<(unsigned long)v%d')
    generate_UINT_LE = _binary('((unsigned long)v%d)<=(unsigned long)v%d')
    generate_UINT_GT = _binary('((unsigned long)v%d)>(unsigned long)v%d')
    generate_UINT_GE = _binary('((unsigned long)v%d)>=(unsigned long)v%d')

    def generate_FAIL(self, f, op):
        for j in range(len(op.args)):
            print >> f, '_c_jit_al[%d]=v%d;' % (j, self.argnum[op.args[j]])
        print >> f, 'return %d;' % self.fn_counter
        self.set_guard_operation(op, self.fn_counter)

    def generate_JUMP(self, f, op):
        if self.simpleloop:
            for j in range(len(op.args)):
                print >> f, 'long w%d=v%d;' % (j, self.argnum[op.args[j]])
            for j in range(len(op.args)):
                print >> f, 'v%d=w%d;' % (j, j)
            print >> f, '}'
        else:
            xxx


class CompilerError(Exception):
    pass
