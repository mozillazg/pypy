
from pypy.translator.avm.test import browsertest as b
from pypy.translator.avm import avm1 as a, avm1gen as g, swf as s, tags as t, records as r

class TestHarness(object):
    def __init__(self, name):
        self.testname  = name
        self.in_test   = False
        self.expected  = []
        self.swf = s.SwfData()
        self.swf.add_tag(t.SetBackgroundColor(0x333333))
        self.swf.add_tag(t.DefineEditText(r.Rect(0, 0, 0, 0), "txt",
                                          "Testing %s." % (name,), color=r.RGBA(0xFFFFFF)))
        self.swf.add_tag(t.PlaceObject(1, 2))
        self.actions = g.AVM1Gen(t.DoAction())
        self.swf.add_tag(self.actions.block)
        self.swf.add_tag(t.ShowFrame())
        self.swf.add_tag(t.End())
        
    def print_text(self, text):
        self.actions.push_const("txt", "\n" + text)
        self.actions.push_var("txt")
        self.actions.swap()
        self.actions.concat_string()
        self.actions.set_variable()

    def print_var(self, prefix, varname):
        self.actions.push_const("txt")
        self.actions.push_var("txt")
        self.actions.push_const("\n" + prefix)
        self.actions.push_var(varname)
        self.actions.concat_string()
        self.actions.concat_string()
        self.actions.set_variable()

    def print_stack(self, prefix):
        self.actions.push_const("txt")
        self.actions.swap()
        self.actions.push_var("txt")
        self.actions.swap()
        self.actions.push_const("\n" + prefix)
        self.actions.swap()
        self.actions.concat_string()
        self.actions.concat_string()
        self.actions.set_variable()
    
    def start_test(self, name):
        assert not self.in_test
        self.in_test = True
        self.print_text("Running test %s." % name)
        self.actions.push_const("result")
        
    def finish_test(self, expected):
        # result value is on the stack,
        # followed by the string "result"
        assert self.in_test
        self.in_test = False
        self.expected.append(expected)
        self.actions.set_variable()
        self.print_var("Got: ", "result")
        self.actions.push_const("/test.result", "") # URL, target
        self.actions.action(a.ActionGetURL2("POST", True, True))

    def do_test(self):
        assert not self.in_test
        with open("test.swf", "w") as f:
            f.write(self.swf.serialize())
        results = b.browsertest(self.testname, self.swf, len(self.expected))
        for e, r in zip(self.expected, results):
            assert e == r
