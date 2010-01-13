
import py
from pypy.translator.avm2.test import browsertest as b
from pypy.translator.avm2 import avm2gen as g

from mech.fusion.swf import swfdata as s, tags as t, records as r
from mech.fusion.avm2 import constants as c, abc_ as a, traits

fl_dis_ns = c.Namespace("flash.display", c.TYPE_NAMESPACE_PackageNamespace)

_test_count = 0

class TestHarness(object):
    def __init__(self, name, gen):
        self.testname  = name
        self.swf = s.SwfData()
        self.swf.add_tag(t.FileAttributes())
        self.swf.add_tag(t.SetBackgroundColor(0x333333))
        self.swf.add_tag(t.DefineEditText(r.Rect(0, 600, 0, 400), "tt",
                                          "Testing %s." % (name,), color=r.RGBA(0xFFFFFF)))
        self.swf.add_tag(t.PlaceObject2(1, 2, name="edittext"))
        self.abc = t.DoABC("PyPy Main")
        self.actions = g.PyPyAvm2ilasm(gen.db, self.abc)
        
        self.swf.add_tag(self.abc)
        self.swf.add_tag(t.SymbolClass({0:"PyPyTest_EntryPoint"}))
        self.swf.add_tag(t.ShowFrame())
        self.swf.add_tag(t.End())

    def get_edittext(self):
        if self.actions.HL('edittext'):
            return self.actions.push_var('edittext')
        
        self.actions.push_this()
        self.actions.emit('getlex', c.QName("edittext"))
        self.actions.store_var('edittext')

    def update_text(self):
        self.get_edittext()
        self.actions.push_var('text')
        self.actions.emit('setproperty', c.QName("text"))
        
    def print_text(self, text):
        self.actions.push_var('text')
        self.actions.push_const("\n" + text)
        self.actions.emit('add')
        self.actions.store_var('text')
        self.update_text()

    def print_var(self, prefix, varname):
        self.actions.push_var('text')
        self.actions.push_const("\n" + prefix)
        self.actions.push_var(varname)
        self.actions.emit('add')
        self.actions.emit('add')
        self.actions.store_var('text')
        self.update_text()

    def print_stack(self, prefix):
        self.actions.push_var('text')
        self.actions.swap()
        self.actions.push_const("\n" + prefix)
        self.actions.swap()
        self.actions.emit('add')
        self.actions.emit('add')
        self.actions.store_var('text')
    
    def start_test(self):
        self.maincls = self.actions.begin_class(c.QName("PyPyTest_EntryPoint"), c.packagedQName("flash.display", "Sprite"))
        self.maincls.make_iinit()
        self.get_edittext()
        self.maincls.add_instance_trait(traits.AbcSlotTrait(c.QName('edittext'), c.packagedQName("flash.text", "TextField")))
        self.actions.push_var('edittext')
        self.actions.emit('getproperty', c.QName('text'))
        self.actions.store_var('text')
        self.print_text("Running test %s." % self.testname)
        
    def finish_test(self):
        # WHEEEEEEE!
        self.actions.store_var('result')
        self.print_var("Got: ", 'result')
        self.actions.emit('findpropstrict', c.packagedQName("flash.net", "URLRequest"))
        self.actions.push_const('./test.result')
        self.actions.emit('constructprop', c.packagedQName("flash.net", "URLRequest"), 1)
        self.actions.store_var('request')
        self.actions.push_var('request')
        self.actions.push_const('POST')
        self.actions.emit('setproperty', c.QName("method"))
        self.actions.push_var('request')
        self.actions.emit('findpropstrict', c.packagedQName("flash.net", "URLVariables"))
        self.actions.emit('constructprop', c.packagedQName("flash.net", "URLVariables"), 0)
        self.actions.emit('setproperty', c.QName("data"))
        self.actions.push_var('request')
        self.actions.emit('getproperty', c.QName("data"))
        self.actions.push_var('result')
        self.actions.emit('setproperty', c.QName("result"))
        self.actions.emit('findpropstrict', c.packagedQName("flash.net", "sendToURL"))
        self.actions.push_var('request')
        self.actions.emit('callpropvoid', c.packagedQName("flash.net", "sendToURL"), 1)
        self.actions.finish()

    def do_test(self, debug=False):
        self.finish_test()
        if debug:
            import sys
            frame = sys._getframe()
            while frame:
                name = frame.f_code.co_name
                if name.startswith("test_"):
                    break
                frame = frame.f_back
            if frame is None:
                global _test_count
                _test_count += 1
                name = "unnamed_test_%s" % (_test_count,)
            f = open("%s.swf" % (name,), "w")
            f.write(self.swf.serialize())
            f.close()
            f = open("%s.abc" % (name,), "w")
            f.write(a.AbcFile.serialize(self.abc))
            f.close()

            asdf
        
        return b.browsertest(name, self.swf)
