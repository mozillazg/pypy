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

ENTRY_POINTS = dict(swf=SWFTestEntryPoint, tamarin=TamarinTestEntryPoint)

def parse_result(string):
    string = string.strip()
    if string == "true":
        return True
    elif string == "false":
        return False
    elif string == "undefined" or string == "null":
        return None
    elif all(c in "123456789-" for c in string):
        return int(string)
    elif "," in string:
        if string.startswith("(") and string.endswith(")"):
            return tuple(parse_result(s) for s in string[1:-1].split(","))
        return [parse_result(s) for s in string.split(",")]
    elif string.startswith("ExceptionWrapper"):
        return eval(string)
    else:
        try:
            return float(string)
        except ValueError:
            pass
    return string

def compile_function(func, name, annotation=[], backendopt=True,
                     exctrans=False, annotatorpolicy=None, wrapexc=False):
    olddefs = patch_os()
    gen = _build_gen(func, annotation, backendopt, exctrans, annotatorpolicy)
    entry_point = ENTRY_POINTS[option.tamtarget](name, gen, wrapexc)
    gen.ilasm = entry_point.actions
    gen.generate_source()
    unpatch_os(olddefs) # restore original values
    return entry_point, gen

def _build_gen(func, annotation, backendopt=True, exctrans=False,
               annotatorpolicy=None):
    try:
        func = func.im_func
    except AttributeError:
        pass
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

    return GenAVM2(tmpdir, t, None, exctrans)

class AVM2Test(BaseRtypingTest, OORtypeMixin):
    def __init__(self):
        self._func = None
        self._ann = None
        self._harness = None

    def _compile(self, fn, args, ann=None, backendopt=True, exctrans=False, wrapexc=False):
        frame = sys._getframe()
        while frame:
            name = frame.f_code.co_name
            if name.startswith("test_"):
                break
            frame = frame.f_back
        else:
            name = "test_unknown"

        if ann is None:
            ann = [lltype_to_annotation(typeOf(x)) for x in args]

        self._entry_point = compile_function(fn, "%s.%s" % (type(self).__name__, name),
            ann, backendopt=backendopt, exctrans=exctrans, wrapexc=wrapexc)
        self._func = fn
        self._ann = ann
        return self._entry_point

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
        entry_point, gen = self._compile(fn, args, annotation,
            backendopt, exctrans, wrapexc)
        entry_point.start_test()
        entry_point.actions.call_graph(gen.translator.graphs[0], args)
        result = parse_result(entry_point.do_test())
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
