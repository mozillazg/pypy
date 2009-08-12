import platform

import py
from pypy.translator.translator import TranslationContext
from pypy.rpython.test.tool import BaseRtypingTest, OORtypeMixin
from pypy.rpython.lltypesystem.lltype import typeOf
from pypy.rpython.ootypesystem import ootype
from pypy.annotation.model import lltype_to_annotation
from pypy.translator.backendopt.all import backend_optimizations
from pypy.translator.backendopt.checkvirtual import check_virtual_methods
from pypy.translator.oosupport.support import patch_os, unpatch_os
from pypy.translator.avm.test.harness import TestHarness

def translate_space_op(gen, op):
    if op.opname == "cast_int_to_char":
        gen.push_arg(op.args[0])
        gen.push_const(1)
        gen.push_var("String")
        gen.call_method("fromCharCode")

def compile_function(func, name, annotation=[], graph=None, backendopt=True,
                     auto_raise_exc=False, exctrans=False,
                     annotatorpolicy=None, nowrap=False):
    olddefs = patch_os()
    gen = _build_gen(func, annotation, name, graph, backendopt,
                     exctrans, annotatorpolicy, nowrap)
    unpatch_os(olddefs) # restore original values
    return gen

def _build_gen(func, annotation, name, graph=None, backendopt=True, exctrans=False,
               annotatorpolicy=None, nowrap=False):
    try: 
        func = func.im_func
    except AttributeError: 
        pass
    t = TranslationContext()
    if graph is not None:
        graph.func = func
        ann = t.buildannotator(policy=annotatorpolicy)
        inputcells = [ann.typeannotation(an) for an in annotation]
        ann.build_graph_types(graph, inputcells)
        t.graphs.insert(0, graph)
    else:
        ann = t.buildannotator(policy=annotatorpolicy)
        ann.build_types(func, annotation)

    t.buildrtyper(type_system="ootype").specialize()
    if backendopt:
        check_virtual_methods(ootype.ROOT)
        backend_optimizations(t)
    
    main_graph = t.graphs[0]

    harness = TestHarness(name)
    harness.actions.begin_function(main_graph.name, [v.name for v in main_graph.getargs()])
    for op in main_graph.startblock.operations:
        translate_space_op(harness.actions, op)
    harness.actions.return_stmt()
    harness.actions.exit_scope()
    
    return harness

class StructTuple(tuple):
    def __getattr__(self, name):
        if name.startswith('item'):
            i = int(name[len('item'):])
            return self[i]
        else:
            raise AttributeError, name

class OOList(list):
    def ll_length(self):
        return len(self)

    def ll_getitem_fast(self, i):
        return self[i]

class InstanceWrapper:
    def __init__(self, class_name):
        self.class_name = class_name

class ExceptionWrapper:
    def __init__(self, class_name):
        self.class_name = class_name

    def __repr__(self):
        return 'ExceptionWrapper(%s)' % repr(self.class_name)

class AVM1Test(BaseRtypingTest, OORtypeMixin):
    def __init__(self):
        self._func = None
        self._ann = None
        self._harness = None
        self._test_count = 1

    def _compile(self, fn, args, ann=None, backendopt=True, auto_raise_exc=False, exctrans=False):
        if ann is None:
            ann = [lltype_to_annotation(typeOf(x)) for x in args]
        if self._func is fn and self._ann == ann:
            return self._harness
        else:
            self._harness = compile_function(fn, self.__class__.__name__, ann,
                                             backendopt=backendopt,
                                             auto_raise_exc=auto_raise_exc,
                                             exctrans=exctrans)
            self._func = fn
            self._ann = ann
            return self._harness

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
    
    def interpret(self, fn, args, expected=None, annotation=None, backendopt=None, exctrans=False):
        backendopt = self._get_backendopt(backendopt)
        harness = self._compile(fn, args, annotation, backendopt=backendopt, exctrans=exctrans)
        harness.start_test("%d" % self._test_count)
        self._test_count += 1
        harness.actions.call_function_constargs(fn.func_name, *args)
        harness.finish_test(expected)

    def do_test(self):
        self._harness.do_test()
    
    def interpret_raises(self, exception, fn, args, backendopt=None, exctrans=False):
        import exceptions # needed by eval
        backendopt = self._get_backendopt(backendopt)
        try:
            self.interpret(fn, args, backendopt=backendopt, exctrans=exctrans)
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
