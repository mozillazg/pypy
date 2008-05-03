import py
from pypy.tool.udir import udir
from pypy.translator.cli.entrypoint import StandaloneEntryPoint
from pypy.translator.cli.gencli import GenCli
from pypy.translator.cli.sdk import SDK
from pypy.jit.codegen.ia32.test.test_genc_portal import I386PortalTestMixin
from pypy.jit.rainbow.test import test_portal
from pypy.jit.codegen.cli.rgenop import RCliGenOp

class CliPortalTestMixin(I386PortalTestMixin):
    RGenOp = RCliGenOp

    def getgraph(self, fn):
        bk = self.rtyper.annotator.bookkeeper
        return bk.getdesc(fn).getuniquegraph()

    def compile(self, ll_main):
        graph = self.getgraph(ll_main)
        entrypoint = StandaloneEntryPoint(graph)
        gen = GenCli(udir, self.rtyper.annotator.translator, entrypoint)
        gen.generate_source()
        self.executable_name = gen.build_exe()

    def cmdexec(self, args=''):
        assert self.executable_name
        mono = ''.join(SDK.runtime())
        return py.process.cmdexec('%s "%s" %s' % (mono, self.executable_name, args))


class TestPortal(CliPortalTestMixin,
                 test_portal.TestPortalOOType):

    # for the individual tests see
    # ====> ../../../rainbow/test/test_portal.py

    def skip(self):
        py.test.skip('in progress')
        
    test_cast_ptr_to_int = skip
