"""
A file that invokes translation of PyGirl with the JIT enabled.
"""

import py, os

from pypy.config.translationoption import set_opt_level, get_combined_translation_config
from pypy.lang.gameboy.profiling.gameboy_profiling_implementation import GameBoyProfiler
from pypy.rpython.annlowlevel import llhelper, llstr, hlstr
from pypy.rpython.lltypesystem.rstr import STR
from pypy.rpython.lltypesystem import lltype
from pypy.translator.goal import unixcheckpoint

config = get_combined_translation_config(translating=True)
config.translation.backendopt.inline_threshold = 0
set_opt_level(config, level='1')
print config

import sys, pdb, time

ROM_PATH = str(py.magic.autopath().dirpath().dirpath().dirpath())+"/lang/gameboy/rom"

gameBoy = GameBoyProfiler()
# an infinite loop
filename = ROM_PATH+"/rom3/rom3.gb"
gameBoy.load_cartridge_file(str(filename), verify=False)
gameBoy.reset()

def entry_point():
    execution_seconds = 600

    start = time.time()
    gameBoy.mainLoop(execution_seconds)
    print time.time() - start
    return 0

def test_run_translation():
    from pypy.translator.goal.ann_override import PyPyAnnotatorPolicy
    from pypy.rpython.test.test_llinterp import get_interpreter

    # first annotate, rtype, and backendoptimize PyPy
    try:
        interp, graph = get_interpreter(entry_point, [], backendopt=True,
                                        config=config)
    except Exception, e:
        print '%s: %s' % (e.__class__, e)
        pdb.post_mortem(sys.exc_info()[2])
        raise

    # parent process loop: spawn a child, wait for the child to finish,
    # print a message, and restart
    unixcheckpoint.restartable_point(auto='run')

    from pypy.jit.tl.gbjit_child import run_child
    run_child(globals(), locals())


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        # debugging: run the code directly
        entry_point()
    else:
        test_run_translation()
