import py, os, sys
from pypy.annotation import model as annmodel
from pypy.rlib.unroll import unrolling_iterable
from pypy.translator.c.genc import CStandaloneBuilder
from pypy.jit.rainbow.test import test_portal
from pypy.jit.codegen.ia32.rgenop import RI386GenOp
from pypy.rpython.annlowlevel import PseudoHighLevelCallable

class I386PortalTestMixin(object):
    RGenOp = RI386GenOp
    translate_support_code = True

    def timeshift_from_portal(self, main, portal, main_args,
                              inline=None, policy=None,
                              backendoptimize=False):
        self.testname = sys._getframe(1).f_code.co_name

        # ---------- translate main() and the support code ----------
        self._timeshift_from_portal(main, portal=portal, main_args=main_args,
                                    inline=inline, policy=policy,
                                    backendoptimize=backendoptimize)

        # ---------- run the stand-alone executable ----------
        cmdargs = ' '.join([str(arg) for arg in main_args])
        output = self.cbuilder.cmdexec(cmdargs)
        lines = output.split()
        lastline = lines[-1]
        assert not lastline.startswith('EXCEPTION:')
        if hasattr(main, 'convert_result'):
            return lastline
        else:
            return int(lastline)    # assume an int


    # The following function is called by _timeshift_from_portal() unless
    # its results are already in the cache from a previous call
    def _serialize(self, main, main_args, portal,
                   policy=None, inline=None,
                   backendoptimize=False):

        # ---------- prepare a stand-alone main() function ----------
        convert_result = getattr(main, 'convert_result', str)
        if hasattr(main, 'convert_arguments'):
            decoders = main.convert_arguments
            assert len(decoders) == len(main_args)
        else:
            decoders = [int] * len(main_args)
        decoders = unrolling_iterable(decoders)
        numargs = len(main_args)
        USAGE = '%s: %d arguments expected\n' % (self.testname, numargs)

        def usage():
            os.write(2, USAGE)
            return 2

        def ll_main(argv):
            if len(argv) != 1 + numargs:
                return usage()
            if len(argv) > 1 and argv[1] == '--help':
                return usage()
            args = ()
            i = 1
            for decoder in decoders:
                args += (decoder(argv[i]),)
                i = i + 1
            try:
                res = main(*args)
            except Exception, e:
                os.write(1, 'EXCEPTION: %s\n' % (e,))
                return 0
            os.write(1, convert_result(res) + '\n')
            return 0

        # ---------- rewire portal and translate everything ----------
        super(I386PortalTestMixin, self)._serialize(
            ll_main, None, portal=portal,
            inline=inline, policy=policy,
            backendoptimize=backendoptimize)

        # ---------- generate a stand-alone executable ----------
        t = self.rtyper.annotator.translator
        t.config.translation.gc = 'boehm'
        self.cbuilder = CStandaloneBuilder(t, ll_main, config=t.config)
        self.cbuilder.generate_source()
        exename = self.cbuilder.compile()
        print '-'*60
        print 'Generated executable for %s: %s' % (self.testname, exename)
        print '-'*60


    def check_insns(self, expected=None, **counts):
        "Cannot check instructions in the generated assembler."


class TestPortal(I386PortalTestMixin,
                 test_portal.TestPortal):

    # for the individual tests see
    # ====> ../../../rainbow/test/test_portal.py
    pass
