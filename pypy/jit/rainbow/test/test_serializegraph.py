import py
from pypy.translator.translator import TranslationContext, graphof
from pypy.jit.hintannotator.annotator import HintAnnotator
from pypy.jit.hintannotator.policy import StopAtXPolicy, HintAnnotatorPolicy
from pypy.jit.hintannotator.model import SomeLLAbstractConstant, OriginFlags
from pypy.jit.codegen.llgraph.rgenop import RGenOp
from pypy.jit.rainbow.codewriter import LLTypeBytecodeWriter, label, tlabel, assemble
from pypy.rlib.jit import hint
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
        writer = LLTypeBytecodeWriter(t, hannotator, RGenOp)
        jitcode = writer.make_bytecode(graph2)
        return writer, jitcode

    def fixpolicy(self, policy):
        return policy

    def test_simple(self):
        def f(x, y):
            return x + y
        writer, jitcode = self.serialize(f, [int, int])
        assert jitcode.code == assemble(writer.interpreter,
                                        "red_int_add", 0, 1,
                                        "make_new_redvars", 1, 2,
                                        "red_return")
        assert len(jitcode.constants) == 0
        assert len(jitcode.typekinds) == 0
        assert jitcode.is_portal
        assert len(jitcode.called_bytecodes) == 0

    def test_constant(self):
        def f(x):
            return x + 1
        writer, jitcode = self.serialize(f, [int])
        assert jitcode.code == assemble(writer.interpreter,
                                        "make_redbox", 1, 0,
                                        "red_int_add", 0, 1,
                                        "make_new_redvars", 1, 2,
                                        "red_return")
        assert len(jitcode.constants) == 1
        assert len(jitcode.typekinds) == 1
        assert len(jitcode.redboxclasses) == 1
        assert jitcode.is_portal
        assert len(jitcode.called_bytecodes) == 0
 
    def test_green_switch(self):
        def f(x, y, z):
            x = hint(x, concrete=True)
            if x:
                return y
            else:
                return z
        writer, jitcode = self.serialize(f, [int, int, int])
        expected = assemble(writer.interpreter,
                            "green_int_is_true", 0,
                            "green_goto_iftrue", 2, tlabel("true"),
                            "make_new_redvars", 1, 1,
                            "make_new_greenvars", 0,
                            label("return"),
                            "red_return",
                            label("true"),
                            "make_new_redvars", 1, 0,
                            "make_new_greenvars", 0,
                            "goto", tlabel("return"),
                            )
        assert jitcode.code == expected
        assert len(jitcode.constants) == 0
        assert len(jitcode.typekinds) == 0
        assert jitcode.is_portal
        assert len(jitcode.called_bytecodes) == 0

    def test_green_switch2(self):
        def f(x, y, z):
            x = hint(x, concrete=True)
            if x:
                return y + z
            else:
                return y - z
        writer, jitcode = self.serialize(f, [int, int, int])
        expected = assemble(writer.interpreter,
                            "green_int_is_true", 0,
                            "green_goto_iftrue", 2, tlabel("true"),
                            "make_new_redvars", 2, 0, 1,
                            "make_new_greenvars", 0,
                            label("sub"),
                            "red_int_sub", 0, 1,
                            "make_new_redvars", 1, 2,
                            label("return"),
                            "red_return",
                            label("true"),
                            "make_new_redvars", 2, 0, 1,
                            "make_new_greenvars", 0,
                            label("add"),
                            "red_int_add", 0, 1,
                            "make_new_redvars", 1, 2,
                            "goto", tlabel("return"),
                            )
        assert jitcode.code == expected
        assert len(jitcode.constants) == 0
        assert len(jitcode.typekinds) == 0
        assert jitcode.is_portal
        assert len(jitcode.called_bytecodes) == 0

    def test_merge(self):
        def f(x, y, z):
            if x:
                a = y - z
            else:
                a = y + z
            return 1 + a
        writer, jitcode = self.serialize(f, [int, int, int])
        expected = assemble(writer.interpreter,
                            "red_int_is_true", 0,
                            "red_goto_iftrue", 3, tlabel("add"),
                            "make_new_redvars", 2, 1, 2,
                            "red_int_add", 0, 1,
                            "make_new_redvars", 1, 2,
                            label("after"),
                            "local_merge", 0, 0,
                            "make_redbox", 1, 0,
                            "red_int_add", 1, 0,
                            "make_new_redvars", 1, 2,
                            "red_return",
                            label("add"),
                            "make_new_redvars", 2, 1, 2,
                            "red_int_sub", 0, 1,
                            "make_new_redvars", 1, 2,
                            "goto", tlabel("after"),
                            )
        assert jitcode.code == expected
        assert len(jitcode.constants) == 1
        assert len(jitcode.typekinds) == 1
        assert jitcode.is_portal
        assert len(jitcode.called_bytecodes) == 0

    def test_loop(self):
        def f(x):
            r = 0
            while x:
                r += x
                x -= 1
            return r
        writer, jitcode = self.serialize(f, [int])
        expected = assemble(writer.interpreter,
                            "make_redbox", 1, 0,
                            "make_new_redvars", 2, 0, 1,
                            "make_new_greenvars", 0,
                            label("while"),
                            "local_merge", 0, 1, 
                            "red_int_is_true", 0,
                            "red_goto_iftrue", 2, tlabel("body"),
                            "make_new_redvars", 1, 0,
                            "make_new_greenvars", 0,
                            "red_return",
                            label("body"),
                            "make_new_redvars", 2, 0, 1,
                            "make_new_greenvars", 0,
                            "red_int_add", 1, 0,
                            "make_redbox", 3, 0,
                            "red_int_sub", 0, 3,
                            "make_new_redvars", 2, 2, 4,
                            "goto", tlabel("while"))
        assert jitcode.is_portal
        assert len(jitcode.called_bytecodes) == 0

    def test_dump_loop(self):
        def f(x):
            r = 0
            while x:
                r += x
                x -= 1
            return r
        writer, jitcode = self.serialize(f, [int])
        import StringIO
        output = StringIO.StringIO()
        jitcode.dump(file=output)
        result = output.getvalue().rstrip()
        print '-' * 40
        print result
        print '-' * 40
        # xxx slightly fragile test, it will break whenever we tweak dump.py
        expected = """\
JITCODE 'f'
pc: 0 |  make_redbox          (0), 0           => r1
    6 |  make_new_redvars     [r0, r1]
      |
   14 |  local_merge          0, None
   20 |  red_int_is_true      r0               => r2
   24 |  red_goto_iftrue      r2, pc: 40
   32 |  make_new_redvars     [r1]
      |
   38 |  red_return
      |
   40 |  make_new_redvars     [r0, r1]
      |
   48 |  red_int_add          r1, r0           => r2
   54 |  make_redbox          (1), 0           => r3
   60 |  red_int_sub          r0, r3           => r4
   66 |  make_new_redvars     [r4, r2]
   74 |  goto                 pc: 14
        """.rstrip()
        assert result == expected

    def test_call(self):
        def g(x):
            return x + 1
        def f(x):
            return g(x) * 2
        writer, jitcode = self.serialize(f, [int])
        assert jitcode.code == assemble(writer.interpreter,
                                        "red_direct_call", 0, 1, 0, 0,
                                        "make_redbox", 1, 0,
                                        "red_int_mul", 1, 2,
                                        "make_new_redvars", 1, 3,
                                        "red_return")
        assert jitcode.is_portal
        assert len(jitcode.called_bytecodes) == 1
        called_jitcode = jitcode.called_bytecodes[0]
        assert called_jitcode.code == assemble(writer.interpreter,
                                               "make_redbox", 1, 0,
                                               "red_int_add", 0, 1,
                                               "make_new_redvars", 1, 2,
                                               "red_return")
        assert not called_jitcode.is_portal
        assert len(called_jitcode.called_bytecodes) == 0

    def test_green_call(self):
        def ll_add_one(x):
            return x+1
        def ll_function(y):
            z = ll_add_one(y)
            z = hint(z, concrete=True)
            return hint(z, variable=True)

        writer, jitcode = self.serialize(ll_function, [int])
        assert jitcode.code == assemble(writer.interpreter,
                                        "green_call", 1, 0, 1, 0,
                                        "make_redbox", 2, 0,
                                        "make_new_redvars", 1, 0,
                                        "make_new_greenvars", 0,
                                        "red_return")
        assert jitcode.is_portal
        assert len(jitcode.called_bytecodes) == 0
        assert len(jitcode.calldescs) == 1
        assert len(jitcode.constants) == 1

    def test_yellow_call(self):
        def ll_two(x):
            if x > 0:
                return 17
            else:
                return 22
        def ll_function(x):
            n = ll_two(x)
            return hint(n+1, variable=True)
        writer, jitcode = self.serialize(ll_function, [int])
        assert jitcode.code == assemble(writer.interpreter,
                                        "yellow_direct_call", 0, 1, 0, 0,
                                        "yellow_retrieve_result",
                                        "green_int_add", 0, 1,
                                        "make_redbox", 2, 0,
                                        "make_new_redvars", 1, 1,
                                        "make_new_greenvars", 0,
                                        "red_return")
        assert jitcode.is_portal
        assert len(jitcode.called_bytecodes) == 1
        called_jitcode = jitcode.called_bytecodes[0]
        assert called_jitcode.code == assemble(writer.interpreter,
                                               "make_redbox", 1, 0,
                                               "red_int_gt", 0, 1,
                                               "red_goto_iftrue", 2, tlabel("true"),
                                               "make_new_redvars", 0,
                                               "make_new_greenvars", 1, 3,
                                               label("return"),
                                               "yellow_return",
                                               label("true"),
                                               "make_new_redvars", 0,
                                               "make_new_greenvars", 1, 5,
                                               "goto", tlabel("return")
                                               )
        assert not called_jitcode.is_portal
        assert len(called_jitcode.called_bytecodes) == 0

class TestLLType(AbstractSerializationTest):
    type_system = "lltype"
