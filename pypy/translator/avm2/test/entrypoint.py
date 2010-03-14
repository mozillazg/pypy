
import py
from pypy.translator.avm2.test.browsertest import browsertest
from pypy.translator.avm2.avm2gen import PyPyAvm2ilasm

from mech.fusion.swf.swfdata import SwfData
from mech.fusion.swf.tags import FileAttributes, SetBackgroundColor, \
     DefineEditText, SymbolClass, PlaceObject2, DoABC, ShowFrame, End
from mech.fusion.swf.records import Rect, RGBA

from mech.fusion.avm2.constants import QName, packagedQName
from mech.fusion.avm2.traits import AbcSlotTrait

class BaseTestEntryPoint(object):
    def __init__(self, name, gen, wrap_exceptions):
        self.excwrap = wrap_exceptions
        self.name  = name
        self.swf = SwfData()
        self.swf.add_tag(FileAttributes())
        self.swf.add_tag(SetBackgroundColor(0x333333))
        self.swf.add_tag(DefineEditText(Rect(0, 0, 600, 400), "", ('''
Running test %s.
If no text saying "Go:" appears below, the test probably had an error.
======================================================================
'''.strip() % (name,)), color=RGBA(0xFFFFFF)))
        self.swf.add_tag(PlaceObject2(1, 2, name="edittext"))
        self.abc = DoABC("PyPy Main")
        self.actions = PyPyAvm2ilasm(gen.db, self.abc)
        
        self.swf.add_tag(self.abc)
        self.swf.add_tag(SymbolClass({0:"PyPyTest_EntryPoint"}))
        self.swf.add_tag(ShowFrame())
        self.swf.add_tag(End())

    def update_text(self):
        pass

    def print_text(self, text):
        self.actions.push_const(text)
        self.actions.store_var('text')
        self.update_text()

    def serialize_swf(self):
        return self.swf.serialize()

    def print_var(self, prefix, varname):
        self.actions.push_const(prefix)
        self.actions.push_var(varname)
        self.actions.emit('add')
        self.actions.store_var('text')
        self.update_text()

    def print_stack(self, prefix, dup=False):
        if dup:
            self.actions.dup()
        self.actions.store_var('text')
        self.update_text()

    def start_test_maincls(self):
        pass
    
    def start_test(self):
        self.start_test_maincls()
        if self.excwrap:
            self.actions.begin_try()
        
    def finish_test(self):
        # WHHEEEEEEE!
        if self.excwrap:
            self.actions.end_try()
            self.actions.emit('convert_s')
            self.actions.branch_unconditionally("PyPy::ExceptionWrapLabel")
            self.actions.begin_catch(QName("Error"))
            self.actions.push_exception()
            self.actions.emit('convert_s')
            self.actions.end_catch()
            self.actions.set_label("PyPy::ExceptionWrapLabel")
        self.actions.store_var('result')
        self.print_var("Got: ", 'result')
        self.publish_test()
        self.epilogue()
        self.actions.finish()

    def do_test(self):
        self.finish_test()
        f = open("%s.swf" % (self.name,), "wb")
        f.write(self.swf.serialize())
        f.close()
        f = open("%s.abc" % (self.name,), "wb")
        f.write(self.abc.serialize())
        f.close()
        return browsertest(self.name, self.swf)

    def epilogue(self):
        pass

    def publish_test(self):
        pass

class SWFTestEntryPoint(BaseTestEntryPoint):
    def get_edittext(self):
        if not self.actions.HL('edittext'):        
            self.actions.push_this()
            self.actions.get_field('edittext')
            self.actions.store_var('edittext')
        self.actions.push_var('edittext')

    def update_text(self):
        self.get_edittext()
        self.actions.push_const("\n")
        self.actions.push_var('text')
        self.actions.emit('add')
        self.actions.emit('callpropvoid', QName("appendText"), 1)

    def start_test_maincls(self):
        self.maincls = self.actions.begin_class(QName("PyPyTest_EntryPoint"), packagedQName("flash.display", "Sprite"))
        self.maincls.make_iinit()
        self.maincls.add_instance_trait(AbcSlotTrait(QName("edittext"), packagedQName("flash.text", "TextField")))

    def publish_test(self):
        self.actions.emit('findpropstrict', packagedQName("flash.net", "URLRequest"))
        self.actions.push_const('./test.result')
        self.actions.emit('constructprop', packagedQName("flash.net", "URLRequest"), 1)
        self.actions.store_var('request')
        self.actions.push_var('request')
        self.actions.push_const('POST')
        self.actions.set_field('method')
        self.actions.push_var('request')
        self.actions.emit('findpropstrict', packagedQName("flash.net", "URLVariables"))
        self.actions.emit('constructprop', packagedQName("flash.net", "URLVariables"), 0)
        self.actions.set_field('data')
        self.actions.push_var('request')
        self.actions.get_field('data')
        self.actions.push_var('result')
        self.actions.set_field('result')
        self.actions.emit('findpropstrict', packagedQName("flash.net", "sendToURL"))
        self.actions.push_var('request')
        self.actions.emit('callpropvoid', packagedQName("flash.net", "sendToURL"), 1)
        self.actions.emit('findpropstrict', packagedQName("flash.net", "navigateToURL"))
        self.actions.emit('findpropstrict', packagedQName("flash.net", "URLRequest"))
        self.actions.push_const('javascript: self.close()')
        self.actions.emit('constructprop', packagedQName("flash.net", "URLRequest"), 1)
        self.actions.push_const('_self')
        self.actions.emit('callpropvoid', packagedQName("flash.net", "navigateToURL"), 2)

class TamarinTestEntryPoint(BaseTestEntryPoint):
    def update_text(self):
        self.actions.push_const("\n")
        self.actions.get_field('text')
        self.actions.emit('add')
        self.actions.emit('findpropstrict', QName("print"))
        self.actions.emit('callpropvoid', QName("print"), 1)

    def epilogue(self):
        self.actions.exit_until_type("script")
        self.actions.push_var('this')
        self.actions.emit('constructprop', QName("PyPyTest_EntryPoint"), 0)

    def start_test_maincls(self):
        self.maincls = self.actions.begin_class(QName("PyPyTest_EntryPoint"))
        self.maincls.make_iinit()
