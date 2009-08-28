from pypy.rpython.lltypesystem import lltype, llmemory, rffi, rstr
from pypy.tool.udir import udir
from pypy.rlib import libffi
from pypy.rlib.objectmodel import we_are_translated
from pypy.jit.metainterp import resoperation, history
from pypy.jit.metainterp.resoperation import ResOperation, rop
from pypy.jit.metainterp.history import AbstractDescr, Box, BoxInt, BoxPtr, INT
from pypy.jit.metainterp.history import ConstPtr
from pypy.jit.backend.x86 import symbolic
import os


class CompilerError(Exception):
    pass


class Compiler:
    FUNCPTR = lltype.Ptr(lltype.FuncType([], rffi.INT))
    CHARPP = lltype.Ptr(lltype.Array(llmemory.GCREF, hints={'nolength': True}))

    def __init__(self, translate_support_code):
        self.fn_counter = 0
        self.filename_counter = 0
        self.c_jit_al = None
        self.c_jit_ap = None
        self.guard_operations = []
        self.translate_support_code = translate_support_code

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
                guard_counter += 1
        #
        funcname = '_c_jit_f%d' % self.fn_counter
        print >> f, 'int %s(){' % funcname
        self.guard_counter = self.fn_counter + 1
        self.argname = {}
        j = 0
        for arg in inputargs:
            assert arg not in self.argname
            self.argname[arg] = name = 'v%d' % j
            if arg.type == INT:
                print >> f, 'long %s=_c_jit_al[%d];' % (name, j)
            else:
                print >> f, 'char*%s=_c_jit_ap[%d];' % (name, j)
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
            ['gcc', '-fomit-frame-pointer', '-O2', basename,
             '-shared', '-o', output_fn],
            cwd=os.path.dirname(fn))
        if retcode != 0:
            raise CompilerError(fn)
        return os.path.join(os.path.dirname(fn), output_fn)

    def load_file(self, fn, loop, funcname):
        handle = libffi.dlopen(fn, libffi.RTLD_GLOBAL | libffi.RTLD_NOW)
        if self.c_jit_al is None:
            c_jit_al = libffi.dlsym(handle, "_c_jit_al")
            c_jit_ap = libffi.dlsym(handle, "_c_jit_ap")
            self.c_jit_al = rffi.cast(rffi.LONGP, c_jit_al)
            self.c_jit_ap = rffi.cast(self.CHARPP, c_jit_ap)
        if funcname is not None:
            c_func = libffi.dlsym(handle, funcname)
            loop._c_jit_func = rffi.cast(self.FUNCPTR, c_func)

    def set_guard_operation(self, op, counter):
        while len(self.guard_operations) <= counter:
            self.guard_operations.append(None)
        self.guard_operations[counter] = op

    # ____________________________________________________________

    def vexpr(self, v):
        if isinstance(v, Box):
            return self.argname[v]
        elif isinstance(v, ConstPtr):
            return str(rffi.cast(lltype.Signed, v.value))
        else:
            return str(v.getint())

    def generate(self, f, op, expr):
        if op.result is None:
            print >> f, '%s;' % expr
        else:
            argname = self.argname
            argname[op.result] = name = 'v%d' % len(argname)
            print >> f, '%s %s=%s;' % (op.result._c_jit_type, name, expr)

    def _unary(expr):
        def generate_unary(self, f, op):
            self.generate(f, op, expr % (self.vexpr(op.args[0]),))
        return generate_unary

    generate_SAME_AS     = _unary('%s')
    generate_INT_IS_TRUE = _unary('%s!=0')
    generate_INT_NEG     = _unary('-%s')
    generate_INT_INVERT  = _unary('~%s')
    generate_BOOL_NOT    = _unary('!%s')

    def _binary(expr):
        def generate_binary(self, f, op):
            self.generate(f, op, expr % (self.vexpr(op.args[0]),
                                         self.vexpr(op.args[1])))
        return generate_binary

    generate_INT_ADD = _binary('%s+%s')
    generate_INT_SUB = _binary('%s-%s')
    generate_INT_MUL = _binary('%s*%s')
    generate_INT_FLOORDIV = _binary('%s/%s')
    generate_INT_MOD = _binary('%s%%%s')
    generate_INT_AND = _binary('%s&%s')
    generate_INT_OR  = _binary('%s|%s')
    generate_INT_XOR = _binary('%s^%s')
    generate_INT_RSHIFT = _binary('%s>>%s')
    generate_INT_LSHIFT = _binary('%s<<%s')
    generate_UINT_RSHIFT = _binary('((unsigned long)%s)>>%s')

    generate_INT_LT = _binary('%s<%s')
    generate_INT_LE = _binary('%s<=%s')
    generate_INT_EQ = _binary('%s==%s')
    generate_INT_NE = _binary('%s!=%s')
    generate_INT_GT = _binary('%s>%s')
    generate_INT_GE = _binary('%s>=%s')
    generate_UINT_LT = _binary('((unsigned long)%s)<(unsigned long)%s')
    generate_UINT_LE = _binary('((unsigned long)%s)<=(unsigned long)%s')
    generate_UINT_GT = _binary('((unsigned long)%s)>(unsigned long)%s')
    generate_UINT_GE = _binary('((unsigned long)%s)>=(unsigned long)%s')

    generate_OOISNULL  = _unary('%s==0')
    generate_OONONNULL = _unary('%s!=0')
    generate_OOIS      = _binary('%s==%s')
    generate_OOISNOT   = _binary('%s!=%s')

    def generate_CALL(self, f, op):
        calldescr = op.descr
        assert isinstance(calldescr, CallDescr)
        args_expr = ','.join([self.vexpr(v_arg) for v_arg in op.args[1:]])
        expr = '((%s)%s)(%s)' % (calldescr.func_c_type, self.vexpr(op.args[0]),
                                 args_expr)
        self.generate(f, op, expr)

    def generate_STRLEN(self, f, op):
        basesize, itemsize, ofs_length = symbolic.get_array_token(rstr.STR,
                                                   self.translate_support_code)
        self.generate(f, op, '*(long*)(%s+%d)' % (self.vexpr(op.args[0]),
                                                  ofs_length))

    def generate_STRGETITEM(self, f, op):
        basesize, itemsize, ofs_length = symbolic.get_array_token(rstr.STR,
                                                   self.translate_support_code)
        self.generate(f, op, '(unsigned char)%s[%d+%s]' % (
            self.vexpr(op.args[0]),
            basesize,
            self.vexpr(op.args[1])))

    def generate_STRSETITEM(self, f, op):
        basesize, itemsize, ofs_length = symbolic.get_array_token(rstr.STR,
                                                   self.translate_support_code)
        print >> f, '%s[%d+%s]=%s;' % (
            self.vexpr(op.args[0]),
            basesize,
            self.vexpr(op.args[1]),
            self.vexpr(op.args[2]))

    def generate_failure(self, f, op, return_expr):
        assert op.opnum == rop.FAIL
        for j in range(len(op.args)):
            box = op.args[j]
            if box.type == INT:
                print >> f, '_c_jit_al[%d]=%s;' % (j, self.vexpr(box))
            else:
                print >> f, '_c_jit_ap[%d]=%s;' % (j, self.vexpr(box))
        print >> f, 'return %s;' % return_expr

    def generate_guard(self, f, op, expr):
        print >> f, 'if (__builtin_expect(%s,0)){' % expr
        fail_op = op.suboperations[0]
        self.generate_failure(f, fail_op, '_c_jit_f%d()' % self.guard_counter)
        self.set_guard_operation(fail_op, self.guard_counter)
        self.guard_counter += 1
        print >> f, '}'

    def generate_GUARD_TRUE(self, f, op):
        self.generate_guard(f, op, '!%s' % self.vexpr(op.args[0]))

    def generate_GUARD_FALSE(self, f, op):
        self.generate_guard(f, op, self.vexpr(op.args[0]))

    def generate_GUARD_VALUE(self, f, op):
        self.generate_guard(f, op, '%s!=%s' % (self.vexpr(op.args[0]),
                                               self.vexpr(op.args[1])))

    def generate_GUARD_NO_EXCEPTION(self, f, op):
        pass  # XXX

    def generate_FAIL(self, f, op):
        self.generate_failure(f, op, str(self.fn_counter))
        self.set_guard_operation(op, self.fn_counter)

    def generate_JUMP(self, f, op):
        if self.simpleloop:
            for j in range(len(op.args)):
                print >> f, '%s w%d=%s;' % (op.args[j]._c_jit_type,
                                            j, self.vexpr(op.args[j]))
            for j in range(len(op.args)):
                print >> f, 'v%d=w%d;' % (j, j)
            print >> f, '}'
        else:
            xxx


# ____________________________________________________________

def get_c_type(TYPE):
    if TYPE is lltype.Void:
        return 'void'
    if isinstance(TYPE, lltype.Ptr):
        return 'char*'
    return _c_type_by_size[rffi.sizeof(TYPE)]

_c_type_by_size = {
    rffi.sizeof(rffi.CHAR): 'char',
    rffi.sizeof(rffi.SHORT): 'short',
    rffi.sizeof(rffi.INT): 'int',
    rffi.sizeof(rffi.LONG): 'long',
    }

def get_class_for_type(TYPE):
    if TYPE is lltype.Void:
        return None
    elif history.getkind(TYPE) == 'ptr':
        return BoxPtr
    else:
        return BoxInt

BoxInt._c_jit_type = 'long'
BoxPtr._c_jit_type = 'char*'

class CallDescr(AbstractDescr):
    call_loop = None

    def __init__(self, arg_classes, ret_class, ret_c_type):
        self.arg_classes = arg_classes
        self.ret_class = ret_class
        self.ret_c_type = ret_c_type
        if arg_classes:
            arg_c_types = [cls._c_jit_type for cls in arg_classes]
            arg_c_types = ','.join(arg_c_types)
        else:
            arg_c_types = 'void'
        self.func_c_type = '%s(*)(%s)' % (ret_c_type, arg_c_types)

    def get_loop_for_call(self, compiler):
        if self.call_loop is None:
            args = [BoxInt()] + [cls() for cls in self.arg_classes]
            if self.ret_class is None:
                result = None
                result_list = []
            else:
                result = self.ret_class()
                result_list = [result]
            operations = [
                ResOperation(rop.CALL, args, result, self),
                ResOperation(rop.GUARD_NO_EXCEPTION, [], None),
                ResOperation(rop.FAIL, result_list, None)]
            operations[1].suboperations = [ResOperation(rop.FAIL, [], None)]
            loop = history.TreeLoop('call')
            loop.inputargs = args
            loop.operations = operations
            compiler.compile_operations(loop)
            self.call_loop = loop
        return self.call_loop
