
from mech.fusion.swf import swfdata as s, tags as t, records as r
from mech.fusion.avm2 import avm2gen as g, constants as c, abc_ as a, traits

fl_dis_ns = c.Namespace("flash.display", c.TYPE_NAMESPACE_PackageNamespace)

swf = s.SwfData()
swf.add_tag(t.FileAttributes())
swf.add_tag(t.SetBackgroundColor(0x333333))
swf.add_tag(t.DefineEditText(r.Rect(0, 600, 0, 400), "tt",
                                  "Testing script order.", color=r.RGBA(0xFFFFFF)))
swf.add_tag(t.PlaceObject2(1, 2, name="edittext"))
abc = t.DoABC()
actions = g.Avm2ilasm(abc, False)

swf.add_tag(abc)
swf.add_tag(t.SymbolClass({0:"ScriptTest_Script0"}))
swf.add_tag(t.ShowFrame())
swf.add_tag(t.End())

actions.context.new_script()
cls = actions.begin_class(c.QName("ScriptTest_Script0"), c.packagedQName("flash.display", "Sprite"), [
        c.packagedQName("flash.display", "Sprite"),
        c.packagedQName("flash.display", "DisplayObjectContainer"),
        c.packagedQName("flash.display", "InteractiveObject"),
        c.packagedQName("flash.display", "DisplayObject"),
        c.packagedQName("flash.events", "EventDispatcher"),
        c.QName("Object"),
        ])
cls.add_instance_trait(traits.AbcSlotTrait(c.QName('edittext'), c.packagedQName("flash.text", "TextField")))
cls.make_cinit()
actions.call_function_constargs("trace", "ScriptTest_Script0 here")
actions.exit_context()
cls.make_iinit()
actions.call_function_constargs("trace", "ScriptTest_Script0 constructed")
actions.emit("findpropstrict", c.QName("ScriptTest_Script1"))
actions.emit("constructprop", c.QName("ScriptTest_Script1"))
actions.store_var("script1")
actions.exit_context()
actions.exit_context()
actions.exit_context()


actions.context.new_script()
cls = actions.begin_class(c.QName("ScriptTest_Script1"))
cls.make_cinit()
actions.call_function_constargs("trace", "ScriptTest_Script1 here")
actions.exit_context()
actions.exit_context()
actions.exit_context()

actions.context.new_script()
cls = actions.begin_class(c.QName("ScriptTest_Script2"))
cls.make_cinit()
actions.call_function_constargs("trace", "ScriptTest_Script2 here")
actions.exit_context()
actions.exit_context()
actions.exit_context()

f = open("test_script.abc", "w")
f.write(a.AbcFile.serialize(abc))
f.close()

f = open("test_script.swf", "w")
f.write(swf.serialize())
f.close()

