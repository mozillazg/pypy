
from pypy.translator.avm1.test import browsertest as b
from pypy.translator.avm1 import avm1 as a, avm1gen as g, swf as s, tags as t, records as r

class TestHarness(object):
    def __init__(self, name):
        self.testname  = name
        self.swf = s.SwfData()
        self.swf.add_tag(t.SetBackgroundColor(0x333333))
        self.swf.add_tag(t.DefineEditText(r.Rect(0, 0, 0, 0), "txt",
                                          "Testing %s." % (name,), color=r.RGBA(0xFFFFFF)))
        self.swf.add_tag(t.PlaceObject2(1, 2))
        self.actions = g.AVM1Gen(t.DoAction())
        self.swf.add_tag(self.actions.block)
        self.swf.add_tag(t.ShowFrame())
        self.swf.add_tag(t.End())
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
        self.actions.action(a.ActionGetURL2("POST", True, True))
        self.actions.push_const("javascript:window.close()", "") # Close the window.
        self.actions.action(a.ActionGetURL2(""))

    def do_test(self, debug=False):
        self.finish_test()
        self.actions.scope.block.seal()
        if debug:
            f = open("test.swf", "w")
            f.write(self.swf.serialize())
            f.close()
        return b.browsertest(self.testname, self.swf)
