from pypy.translator.translator import TranslationContext, graphof
from pypy.jit.hintannotator.annotator import HintAnnotator
from pypy.jit.hintannotator.policy import StopAtXPolicy, HintAnnotatorPolicy
from pypy.jit.hintannotator.model import SomeLLAbstractConstant, OriginFlags
from pypy.jit.rainbow.bytecode import BytecodeWriter
from pypy.jit.codegen.llgraph.rgenop import RGenOp
from pypy import conftest


P_DEFAULT = HintAnnotatorPolicy(entrypoint_returns_red=False)
P_OOPSPEC = HintAnnotatorPolicy(oopspec=True,
                                entrypoint_returns_red=False)
P_OOPSPEC_NOVIRTUAL = HintAnnotatorPolicy(oopspec=True,
                                          novirtualcontainer=True,
                                          entrypoint_returns_red=False)
P_NOVIRTUAL = HintAnnotatorPolicy(novirtualcontainer=True,
                                  entrypoint_returns_red=False)

class AbstractSerializationTest:
    type_system = None
    
    def serialize(self, func, argtypes, policy=P_DEFAULT, inline=None,
                  backendoptimize=False):
        # build the normal ll graphs for ll_function
        t = TranslationContext()
        a = t.buildannotator()
        a.build_types(func, argtypes)
        rtyper = t.buildrtyper(type_system = self.type_system)
        rtyper.specialize()
        if inline:
            auto_inlining(t, threshold=inline)
        if backendoptimize:
            from pypy.translator.backendopt.all import backend_optimizations
            backend_optimizations(t)
        graph1 = graphof(t, func)

        # build hint annotator types
        policy = self.fixpolicy(policy)
        hannotator = HintAnnotator(base_translator=t, policy=policy)
        hs = hannotator.build_types(graph1, [SomeLLAbstractConstant(v.concretetype,
                                                                    {OriginFlags(): True})
                                             for v in graph1.getargs()])
        hannotator.simplify()
        t = hannotator.translator
        if conftest.option.view:
            t.view()
        graph2 = graphof(t, func)
        writer = BytecodeWriter(t, hannotator, RGenOp)
        jitcode = writer.make_bytecode(graph2)
        return writer, jitcode

    def fixpolicy(self, policy):
        return policy

    def test_simple(self):
        def f(x, y):
            return x + y
        writer, jitcode = self.serialize(f, [int, int])
        assert jitcode.code == code(writer.interpreter,
                                    "red_int_add", 0, 1,
                                    "make_new_redvars", 1, 2,
                                    "make_new_greenvars", 0,
                                    "red_return", 0)

    def test_switch(self):
        def f(x, y, z):
            if x:
                return y
            else:
                return z
        writer, jitcode = self.serialize(f, [int, int, int])
        expected = code(writer.interpreter,
                        "red_int_is_true", 0,
                        "red_goto_iftrue", 3, tlabel("true"),
                        "make_new_redvars", 1, 2,
                        "make_new_greenvars", 0,
                        label("return"),
                        "red_return", 0,
                        label("true"),
                        "make_new_redvars", 1, 1,
                        "make_new_greenvars", 0,
                        "goto", tlabel("return"),
                        )
        assert jitcode.code == expected


class label(object):
    def __init__(self, name):
        self.name = name

class tlabel(object):
    def __init__(self, name):
        self.name = name

def code(interpreter, *args):
    result = []
    labelpos = {}
    def emit_2byte(index):
        result.append(chr((index >> 8) & 0xff))
        result.append(chr(index & 0xff))
    for arg in args:
        if isinstance(arg, str):
            emit_2byte(interpreter.find_opcode(arg))
        elif isinstance(arg, int):
            emit_2byte(arg)
        elif isinstance(arg, label):
            labelpos[arg.name] = len(result)
        elif isinstance(arg, tlabel):
            result.extend((arg, None, None, None))
        else:
            XXX
    for i in range(len(result)):
        b = result[i]
        if isinstance(b, tlabel):
            index = labelpos[b.name]
            result[i + 0] = chr((index >> 24) & 0xff)
            result[i + 1] = chr((index >> 16) & 0xff)
            result[i + 2] = chr((index >>  8) & 0xff)
            result[i + 3] = chr(index & 0xff)
    return "".join(result)



class TestLLType(AbstractSerializationTest):
    type_system = "lltype"
