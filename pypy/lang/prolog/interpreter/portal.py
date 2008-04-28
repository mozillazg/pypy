from pypy.jit.hintannotator.policy import ManualGraphPolicy
from pypy.lang.prolog.interpreter import term, engine, helper
from pypy.translator.translator import graphof


forbidden_modules = {'pypy.lang.prolog.interpreter.parser': True,
                     }


class PyrologHintAnnotatorPolicy(ManualGraphPolicy):
    hotpath = True

    def look_inside_graph_of_module(self, graph, func, mod):
        if mod in forbidden_modules:
            return False
        return True


def get_portal(drv):
    t = drv.translator
    portal = getattr(PORTAL, 'im_func', PORTAL)

    policy = PyrologHintAnnotatorPolicy()
    policy.seetranslator(t)
    return portal, policy
