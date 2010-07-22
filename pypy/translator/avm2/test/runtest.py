import platform
import sys

import py
from pypy.conftest import option
from pypy.translator.translator import TranslationContext
from pypy.rpython.test.tool import BaseRtypingTest, OORtypeMixin
from pypy.rpython.lltypesystem.lltype import typeOf
from pypy.rpython.ootypesystem import ootype
from pypy.annotation.model import lltype_to_annotation
from pypy.translator.backendopt.all import backend_optimizations
from pypy.translator.backendopt.checkvirtual import check_virtual_methods
from pypy.translator.oosupport.support import patch_os, unpatch_os
from pypy.translator.avm2.test.entrypoint import SWFTestEntryPoint, TamarinTestEntryPoint
from pypy.translator.avm2.test.browsertest import ExceptionWrapper, InstanceWrapper
from pypy.translator.avm2.genavm import GenAVM2

class UnparsableResult(Exception):
    pass

def parse_result(string):
    string = string.strip()
    if string.startswith("Got:"):
        return parse_result_raw(string[4:].strip())
    elif string.startswith("ExceptionWrapper"):
        return eval(string.splitlines()[0])
    raise UnparsableResult(string)

def parse_result_raw(string):
    if string == "":
        return ""
    if string == "true":
        return True
    if string == "false":
        return False
    if string == "undefined" or string == "null":
        return None
    if string[0] + string[-1] in ('()', '[]'):
        res = [parse_result_raw(s) for s in string[1:-1].split(",")]
        return tuple(res) if string[0] == '(' else res
    try:
        return int(string)
    except ValueError:
        pass
    try:
        return float(string)
    except ValueError:
        pass
    return string

def compile_function(func, name, annotation, backendopt=True,
                     exctrans=False, annotatorpolicy=None, wrapexc=False):
    olddefs = patch_os()
    gen = _build_gen(func, name, annotation, backendopt,
                     exctrans, annotatorpolicy, wrapexc)
    gen.generate_source()
    gen.entrypoint.finish_compiling()
    unpatch_os(olddefs) # restore original values
    return gen

def _build_gen(func, name, annotation, backendopt=True,
               exctrans=False,  annotatorpolicy=None, wrapexc=False):
    func = getattr(func, "im_func", func)

    t = TranslationContext()
    ann = t.buildannotator(policy=annotatorpolicy)
    ann.build_types(func, annotation)

    t.buildrtyper(type_system="ootype").specialize()
    if backendopt:
        check_virtual_methods(ootype.ROOT)
        backend_optimizations(t)

    if option.view:
        t.view()

    tmpdir = py.path.local('.')

    if option.browsertest:
        entry = SWFTestEntryPoint
    else:
        entry = TamarinTestEntryPoint
    ep = entry(name, t.graphs[0], wrapexc)

    return GenAVM2(tmpdir, t, ep, exctrans)

class AVM2Test(BaseRtypingTest, OORtypeMixin):
    def __init__(self):
        self._func = None
        self._ann = None
        self._entry_point = None

    def _compile(self, fn, ann=None, backendopt=True, exctrans=False, wrapexc=False):
        frame = sys._getframe()
        while frame:
            name = frame.f_code.co_name
            if name.startswith("test_"):
                break
            frame = frame.f_back
        else:
            name = "test_unknown"

        if fn == self._func and self._ann == ann:
            return self._gen
        self._gen = compile_function(fn, "%s.%s" % (type(self).__name__, name),
            ann, backendopt=backendopt, exctrans=exctrans, wrapexc=wrapexc)
        self._func = fn
        self._ann = ann
        return self._gen

    def _skip_win(self, reason):
        if platform.system() == 'Windows':
            py.test.skip('Windows --> %s' % reason)

    def _skip_powerpc(self, reason):
        if platform.processor() == 'powerpc':
            py.test.skip('PowerPC --> %s' % reason)

    def _skip_llinterpreter(self, reason, skipLL=True, skipOO=True):
        pass

    def _get_backendopt(self, backendopt):
        if backendopt is None:
            backendopt = getattr(self, 'backendopt', True) # enable it by default
        return backendopt

    def interpret(self, fn, args, annotation=None, backendopt=None,
                  exctrans=False, wrapexc=False):
        backendopt = self._get_backendopt(backendopt)
        if annotation is None:
            annotation = [lltype_to_annotation(typeOf(x)) for x in args]
        gen = self._compile(fn, annotation,
               backendopt, exctrans, wrapexc)
        result = parse_result(gen.entrypoint.run_test(args))
        if isinstance(result, ExceptionWrapper):
            raise result
        return result

    def interpret_raises(self, exception, fn, args, backendopt=None,
                         exctrans=False):
        import exceptions # needed by eval
        backendopt = self._get_backendopt(backendopt)
        try:
            self.interpret(fn, args, backendopt=backendopt, exctrans=exctrans, wrapexc=True)
        except ExceptionWrapper, ex:
            assert issubclass(eval(ex.class_name), exception)
        else:
            assert False, 'function did raise no exception at all'

    float_eq = BaseRtypingTest.float_eq_approx

    def is_of_type(self, x, type_):
        return True # we can't really test the type

    def ll_to_string(self, s):
        return s

    def ll_to_unicode(self, s):
        return s

    def ll_to_list(self, l):
        return l

    def ll_to_tuple(self, t):
        return t

    def class_name(self, value):
        return value.class_name.split(".")[-1]

    def is_of_instance_type(self, val):
        return isinstance(val, InstanceWrapper)

    def read_attr(self, obj, name):
        py.test.skip('read_attr not supported on gencli tests')
