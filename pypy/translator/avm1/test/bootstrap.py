import autopath

from mech.fusion.swf import swfdata as s, tags as t, records as r
from mech.fusion import avm1 as a

if __name__ == "__main__":
    with open("test.swf", "w") as f:
        data = s.SwfData()
        data.add_tag(t.SetBackgroundColor(0x333333))
        data.add_tag(t.DefineEditText(r.Rect(0, 0, 0, 0), "txt", "Testing!", color=r.RGBA(0xFFFFFF)))
        data.add_tag(t.PlaceObject(1, 2))
        actions = t.DoAction()
        actions.add_action(a.ActionPush("txt", "txt"))
        actions.add_action(a.ActionGetVariable())
        actions.add_action(a.ActionPush("\nTesting 2!"))
        actions.add_action(a.ActionStringAdd())
        actions.add_action(a.ActionSetVariable())
        actions.add_action(a.ActionPush("/test.result", ""))
        actions.add_action(a.ActionGetURL2("POST"))
        data.add_tag(actions)
        data.add_tag(t.ShowFrame())
        data.add_tag(t.End())
        f.write(data.serialize())
