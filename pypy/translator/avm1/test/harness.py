
from pypy.translator.avm1.test.browsertest import browsertest
from mech.fusion.swf.swfdata import SwfData
from mech.fusion.swf.records import Rect, RGBA
from mech.fusion.swf import tags
from mech.fusion.avm1.avm1gen import AVM1Gen
from mech.fusion.avm1.actions import ActionGetURL2

class TestHarness(object):
    def __init__(self, name):
        self.testname  = name
        self.swf = SwfData()
        self.swf.add_tag(tags.SetBackgroundColor(0x333333))
        self.swf.add_tag(tags.DefineEditText(Rect(0, 0, 0, 0), "txt",
                        "Testing %s." % (name,), color=RGBA(0xFFFFFF)))
        self.swf.add_tag(tags.PlaceObject2(1, 1))
        self.actions = AVM1Gen(tags.DoAction())
        self.swf.add_tag(self.actions.block)
        self.swf.add_tag(tags.ShowFrame())
        self.swf.add_tag(tags.End())
        self.start_test()
        
    def print_text(self, text):
        self.actions.push_const("txt", "\n" + text)
        self.actions.push_var("txt")
        self.actions.swap()
        self.actions.emit('typed_add')
        self.actions.set_variable()

    def print_var(self, prefix, varname):
        self.actions.push_const("txt")
        self.actions.push_var("txt")
        self.actions.push_const("\n" + prefix)
        self.actions.push_var(varname)
        self.actions.emit('typed_add')
        self.actions.emit('typed_add')
        self.actions.set_variable()

    def print_stack(self, prefix):
        self.actions.push_const("txt")
        self.actions.swap()
        self.actions.push_var("txt")
        self.actions.swap()
        self.actions.push_const("\n" + prefix)
        self.actions.swap()
        self.actions.emit('typed_add')
        self.actions.emit('typed_add')
        self.actions.set_variable()
    
    def start_test(self):
        self.print_text("Running test %s." % self.testname)
        self.actions.push_const("result")
        
    def finish_test(self):
        # result value is on the stack,
        # followed by the string "result"
        self.actions.set_variable()
        self.print_var("Got: ", "result")
        self.actions.push_const("/test.result", "") # URL, target
        self.actions.action(ActionGetURL2("POST", True, True))
        self.actions.push_const("javascript:window.close()", "") # Close the window.
        self.actions.action(ActionGetURL2(""))

    def do_test(self, debug=False):
        self.finish_test()
        self.actions.scope.block.seal()
        if debug:
            f = open("test.swf", "w")
            f.write(self.swf.serialize())
            f.close()
        return browsertest(self.testname, self.swf)
