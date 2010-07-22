
import py
import subprocess

from pypy.conftest import option
from pypy.rpython.ootypesystem import ootype
from pypy.translator.avm2.test.browsertest import browsertest
from pypy.translator.avm2.codegen import PyPyCodeGenerator
from pypy.translator.avm2.entrypoint import BaseEntryPoint

from mech.fusion.swf import tags
from mech.fusion.swf.swfdata import SwfData
from mech.fusion.swf.records import Rect, RGBA

from mech.fusion.avm2.abc_ import AbcFile
from mech.fusion.avm2.constants import QName, packagedQName, MultinameL
from mech.fusion.avm2.traits import AbcSlotTrait

class BaseTestEntryPoint(BaseEntryPoint):
    def __init__(self, name, graph, excwrap):
        self.name  = name
        self.graph = graph
        self.excwrap = excwrap
        self.maincls_name = packagedQName("PyPyTest", name)

    def get_name(self):
        return self.name

    def dependencies(self):
        self.db.pending_function(self.graph)

    def render(self, ilasm):
        self.actions = ilasm
        self.prologue()
        self.start_test()
        self.call_test()
        self.finish_test()

    def prologue(self):
        pass

    def call_test(self):
        qname = self.actions.cts.graph_to_qname(self.graph)
        if self.excwrap:
            self.actions.begin_try()
        self.actions.emit('findpropstrict', qname)
        self.gather_arguments()
        self.actions.emit('callproperty', qname, len(self.graph.getargs()))

    def finish_test(self):
        # WHHEEEEEEEE!
        if self.excwrap:
            self.actions.end_try()
            self.actions.branch_unconditionally("PyPy::ExceptionWrapLabel")
            self.actions.begin_catch(QName("Error"))
            self.actions.push_exception()
            self.actions.emit('convert_s')
            self.actions.end_catch()
            self.actions.set_label("PyPy::ExceptionWrapLabel")
        self.publish_test()
        self.actions.exit_until_type("script")

    def publish_test(self):
        pass

    def gather_arguments(self):
        pass

    def finish_compiling(self):
        self.epilogue()
        self.actions.finish()
        self.save_test()

    def epilogue(self):
        pass

    def save_test(self):
        pass

    def run_test(self, args):
        pass

class SWFTestEntryPoint(BaseTestEntryPoint):
    def prologue(self):
        self.swf = SwfData()
        self.swf.add_tag(tags.FileAttributes())
        self.swf.add_tag(tags.SetBackgroundColor(0x333333))
        self.swf.add_tag(tags.DefineEditText(Rect(0, 0, 600, 400), "", ('''
Running test %s. If no text saying "Got: "
appears below, the test probably had an error.
==================================================
'''.strip() % (self.name,)), color=RGBA(0xFFFFFF)))
        self.swf.add_tag(tags.PlaceObject2(1, 1, name="edittext"))
        self.swf.add_tag(tags.DoABC("PyPy Main", self.actions.abc))
        self.swf.add_tag(tags.SymbolClass({0:"PyPyTest::" + self.name}))
        self.swf.add_tag(tags.ShowFrame())
        self.swf.add_tag(tags.End())

    def save_test(self):
        barename = py.path.local(self.name + ".flash")
        barename.new(ext=".swf").write(self.swf.serialize(), mode="wb")
        barename.new(ext=".abc").write(self.actions.abc.serialize(), mode="wb")

    def run_test(self, args):
        return browsertest(self.name, self.swf)

    def get_edittext(self):
        if not self.actions.HL('edittext'):
            self.actions.push_this()
            self.actions.get_field('edittext')
            self.actions.store_var('edittext')
        self.actions.push_var('edittext')

    def update_text(self):
        self.get_edittext()
        self.actions.load("\n")
        self.actions.push_var('text')
        self.actions.emit('add')
        self.actions.emit('callpropvoid', QName("appendText"), 1)

    def start_test(self):
        self.maincls = self.actions.begin_class(self.maincls_name,
                            packagedQName("flash.display", "Sprite"))
        self.maincls.make_iinit()
        self.maincls.add_instance_trait(AbcSlotTrait(QName("edittext"),
                            packagedQName("flash.text", "TextField")))

    def publish_test(self):
        self.actions.store_var('text')
        self.update_text()
        self.actions.emit('findpropstrict', packagedQName("flash.net", "URLRequest"))
        self.actions.load('./test.result')
        self.actions.emit('constructprop', packagedQName("flash.net", "URLRequest"), 1)
        self.actions.store_var('request')
        self.actions.push_var('request')
        self.actions.load('POST')
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
        self.actions.load('javascript: self.close()')
        self.actions.emit('constructprop', packagedQName("flash.net", "URLRequest"), 1)
        self.actions.load('_self')
        self.actions.emit('callpropvoid', packagedQName("flash.net", "navigateToURL"), 2)

class TamarinTestEntryPoint(BaseTestEntryPoint):
    def save_test(self):
        abc = py.path.local(self.name+".tamarin.abc")
        abc.write(AbcFile.serialize(self.actions.abc), "wb")

    def run_test(self, args):
        procargs = [option.tamexec, self.name + ".tamarin.abc", "--"] + map(str, args)
        testproc = subprocess.Popen(procargs, stdout=subprocess.PIPE)
        return testproc.stdout.read()

    def publish_test(self):
        self.actions.emit('findpropstrict', QName("print"))
        self.actions.swap()
        self.actions.emit('callpropvoid', QName("print"), 1)

    def gather_arguments(self):
        self.actions.load(dict(False=False, True=True))
        self.actions.store_var("booltable")
        self.actions.load(packagedQName("avmplus", "System"))
        self.actions.get_field("argv")
        for index, arg in enumerate(self.graph.getargs()):
            if arg.concretetype is not ootype.Void:
                self.actions.dup()
                if arg.concretetype is ootype.Bool:
                    self.actions.get_field(str(index))
                    self.actions.push_var("booltable")
                    self.actions.swap()
                    self.actions.emit('getproperty', MultinameL())
                else:
                    self.actions.get_field(str(index), arg.concretetype)
                self.actions.swap()
        self.actions.pop()

    def epilogue(self):
        self.actions.exit_until_type("script")
        self.actions.context.make_init()
        self.actions.push_this()
        self.actions.emit('constructprop', self.maincls_name, 0)

    def start_test(self):
        self.maincls = self.actions.begin_class(self.maincls_name)
        self.maincls.make_iinit()
