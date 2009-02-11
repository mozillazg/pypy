
import py
from codegen386.runner import CPU386
from test.test_zrpy_basic import LLInterpJitMixin
from pypy.jit.hintannotator.policy import StopAtXPolicy
from test.test_slist import ListTests
from pypy.rpython.lltypesystem import lltype
from pyjitpl import build_meta_interp
from rpyjitpl import set_ll_helper
from pypy.translator.c.genc import CStandaloneBuilder as CBuilder
from pypy.annotation.listdef import s_list_of_strings
from pypy.annotation import model as annmodel
from history import log

_cache = (None,)

def rpython_ll_meta_interp(function, args, loops=None, **kwds):
    global _cache
    key = (function, tuple([lltype.typeOf(arg) for arg in args]))
    lgt = len(args)

    src = py.code.Source("""
    def entry_point(argv):
        args = (%s,)
        res, num_loops = boot1(*args)
        print "%%d,%%d" %% (res, num_loops)
        return 0
    """ % (", ".join(['int(argv[%d])' % (i + 1) for i in range(lgt)]),))

    if key != _cache[0]:
        _cache = (None,)
        type_system = 'lltype'
        kwds['translate_support_code'] = True
        metainterp = build_meta_interp(function, args, type_system, **kwds)
        boot_graph = set_ll_helper(metainterp,
                                   [lltype.typeOf(arg) for arg in args])
        boot1 = boot_graph.func
        exec src.compile() in locals()
        mixlevelann = metainterp.cpu.mixlevelann
        entry_point_graph = mixlevelann.getgraph(entry_point,
                                                 [s_list_of_strings],
                                                 annmodel.SomeInteger())
        metainterp.cpu.mixlevelann.finish()
        del metainterp.cpu.mixlevelann
        _cache = (key, metainterp, boot_graph)
    
    metainterp = _cache[1]
    boot_graph = _cache[2]
    t = metainterp.cpu.rtyper.annotator.translator
    t.config.translation.gc = 'boehm'
    cbuilder = CBuilder(t, entry_point, config=t.config)
    cbuilder.generate_source()
    exe_name = cbuilder.compile()
    log('---------- Test starting ----------')
    stdout = cbuilder.cmdexec(" ".join([str(arg) for arg in args]))
    stdout.split(',')
    res_s, loops_s = stdout.split(',')
    res = int(res_s)
    actual_loops = int(loops_s)
    log('---------- Test done ----------')
    if loops is not None:
        actual_loops = results.item1
        assert actual_loops == loops
    return res


class Jit386Mixin(LLInterpJitMixin):
    @staticmethod
    def meta_interp(fn, args, **kwds):
        return rpython_ll_meta_interp(fn, args, CPUClass=CPU386, **kwds)

class TestSList(Jit386Mixin, ListTests):
    # for the individual tests see
    # ====> ../../test/test_slist.py
    pass

