
import py, os, re, subprocess
from pypy.translator.translator import TranslationContext
from pypy.translator.backendopt.all import backend_optimizations
from pypy.translator.avm.avm import AVM1
from pypy.translator.avm.test.browsertest import browsertest, TestCase
# from pypy.translator.avm import conftest
from pypy.translator.avm.log import log
from pypy.conftest import option
from pypy.rpython.test.tool import BaseRtypingTest, OORtypeMixin
from pypy.rlib.nonconst import NonConstant
from pypy.rpython.ootypesystem import ootype

from pypy.rpython.llinterp import LLException

log = log.runtest

class AVM1Exception(object):

class compile_function(object):
    def __init__(self, function, annotations, stackless=False, view=False, root=None, policy=None):
        
        t = TranslationContext()
        
        if policy is None:
            from pypy.annotation.policy import AnnotatorPolicy
            policy = AnnotatorPolicy()
            policy.allow_someobjects = False

        self.root = root
        
        ann = t.buildannotator(policy=policy)
        ann.build_types(function, annotations)
        if view or option.view:
            t.view()

        t.buildrtyper(type_system="ootype").specialize()

        if view or option.view:
            t.view()

        self.avm = AVM1(t, function, stackless)

    def _conv(self, v):
        if isinstance(v, str):
            return repr(v)
        return str(v).lower()
    
    def call(self, entry_function):

        if entry_function is None:
            entry_function = self.avm.translator.graphs[0].name
        else:
            entry_function = self.avm.translator.annotator.bookeeper.getdesc(entry_function).cached_graph(None)

        output = browsertest("Test Name", self.avm.serialize())
        return self.reinterpret(output)

    @classmethod
    def reinterpret(cls, s):
        if s == 'false':
            return False
        elif s == 'true':
            return True
        elif s == 'undefined' or s == 'null':
            return None
        elif s == 'inf':
            return 1e400
        elif s == 'NaN':
            return 1e400 / 1e400
        elif s.startswith('[') or s.startswith('('):
            contents = s[1:-1].split(',')
            return [self.reintepret(i) for i in contents]
        else:
            try:
                res = float(s)
                if float(int(res)) == float(res):
                    return int(res)
                return res
            except ValueError:
                return str(s)

class AVM1Test(BaseRtypingTest, OORtypeMixin):
    def _compile(self, _fn, args, policy=None):
        argnames = _fn.func_code.co_varnames[:_fn.func_code.co_argcount]
        func_name = _fn.func_name
        if func_name == '<lambda>':
            func_name = 'func'
        source = py.code.Source("""
        def %s():
            from pypy.rlib.nonconst import NonConstant
            res = _fn(%s)
            if isinstance(res, type(None)):
                return None
            else:
                return str(res)"""
        % (func_name, ",".join(["%s=NonConstant(%r)" % (name, i) for
                                    name, i in zip(argnames, args)])))
        exec source.compile() in locals()
        return compile_function(locals()[func_name], [], policy=policy)

    def interpret(self, fn, args, policy=None):
        f = self.compile(fn, args, policy)
        res = f(*args)
        return res

    def interpret_raises(self, exception, fn, args):
        try:
            res = self.interpret(fn, args)
        except AVM1Exception, e:
            s = e.args[0]
            assert s.startswith('uncaught exception')
            assert re.search(exception.__name__, s)
        else:
            raise AssertionError("Did not raise, returned %s" % res)

    def string_to_ll(self, s):
        return s

    def ll_to_string(self, s):
        return str(s)

    def ll_to_list(self, l):
        return l

    def ll_unpack_tuple(self, t, length):
        assert len(t) == length
        return tuple(t)

    def class_name(self, value):
        return value[:-8].split('.')[-1]

    def is_of_instance_type(self, val):
        m = re.match("^<.* object>$", val)
        return bool(m)

    def read_attr(self, obj, name):
        py.test.skip('read_attr not supported on genavm tests')

def check_source_contains(compiled_function, pattern):
