import py
from pypy.lang.js.interpreter import *
from pypy.lang.js.jsobj import W_Array, W_String
from pypy.rlib.parsing.parsing import ParseError
from py.__.test.outcome import Failed, ExceptionFailure
import pypy.lang.js as js
from pypy.lang.js import interpreter
from pypy.lang.js.execution import JsBaseExcept

interpreter.TEST = True

rootdir = py.magic.autopath().dirpath()
exclusionlist = ['shell.js', 'browser.js']

def overriden_evaljs(ctx, args, this):
    try:
        w_eval = W_Eval(ctx)
        return w_eval.Call(ctx, args, this)
    except JsBaseExcept:
        return W_String("error")

passing_tests = ['Number', 'Boolean', 'Array']

class EcmatestPlugin:
    def pytest_addoption(self, parser):
        parser.addoption('--ecma',
               action="store_true", dest="ecma", default=False,
               help="run js interpreter ecma tests"
        )

    def pytest_collect_file(self, path, parent):
        if parent.name not in passing_tests:
            return
        if path.ext == ".js" and path.basename not in exclusionlist:
            if not parent.config.option.ecma:
                py.test.skip("ECMA tests disabled, run with --ecma")
            return JSTestFile(path, parent=parent)

ConftestPlugin = EcmatestPlugin

class JSTestFile(py.test.collect.File):
    def init_interp(cls):
        if hasattr(cls, 'interp'):
            cls.testcases.PutValue(W_Array(), cls.interp.global_context)
            cls.tc.PutValue(W_IntNumber(0), cls.interp.global_context)

        cls.interp = Interpreter()
        shellpath = rootdir/'shell.js'
        if not hasattr(cls, 'shellfile'):
            cls.shellfile = load_file(str(shellpath))
        cls.interp.run(cls.shellfile)
        cls.testcases = cls.interp.global_context.resolve_identifier(cls.interp.global_context, 'testcases')
        cls.tc = cls.interp.global_context.resolve_identifier(cls.interp.global_context, 'tc')
        # override eval
        cls.interp.w_Global.Put(cls.interp.global_context, 'eval', W_Builtin(overriden_evaljs))
        
    init_interp = classmethod(init_interp)
    
    def __init__(self, fspath, parent=None):
        super(JSTestFile, self).__init__(fspath, parent)
        self.name = fspath.purebasename
        self.fspath = fspath
          
    def collect(self):
        if py.test.config.option.collectonly:
            return
        self.init_interp()
        #actually run the file :)
        t = load_file(str(self.fspath))
        try:
            self.interp.run(t)
        except ParseError, e:
            raise Failed(msg=e.nice_error_message(filename=str(self.fspath)), excinfo=None)
        except JsBaseExcept:
            raise Failed(msg="Javascript Error", excinfo=py.code.ExceptionInfo())
        except:
            raise
        ctx = self.interp.global_context
        testcases = ctx.resolve_identifier(ctx, 'testcases')
        self.tc = ctx.resolve_identifier(ctx, 'tc')
        testcount = testcases.Get(ctx, 'length').ToInt32(ctx)
        self.testcases = testcases
        return [JSTestItem(number, parent=self) for number in range(testcount)]

class JSTestItem(py.test.collect.Item):
    def __init__(self, number, parent=None):
        super(JSTestItem, self).__init__(str(number), parent)
        self.number = number
        
    def runtest(self):
        ctx = JSTestFile.interp.global_context
        r3 = ctx.resolve_identifier(ctx, 'run_test')
        w_test_number = W_IntNumber(self.number)
        result = r3.Call(ctx=ctx, args=[w_test_number]).ToString()
        __tracebackhide__ = True
        if result != "passed":
            raise Failed(msg=result)

    _handling_traceback = False
    def _getpathlineno(self):
        return self.parent.parent.fspath, 0 

