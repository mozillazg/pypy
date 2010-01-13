import autopath

from pypy.translator.avm1.test import browsertest, harness as h
from mech.fusion import avm1 as a

def test_harness():
    harness = h.TestHarness("harness")
    harness.start_test("harness")
    harness.actions.add_action(a.ActionPush(True))
    harness.finish_test(True)
    harness.do_test()

if __name__ == "__main__":
    test_harness()
