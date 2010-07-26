
from pypy.translator.avm2 import types_ as types

from mech.fusion.avm2.traits import AbcSlotTrait
from mech.fusion.avm2.constants import packagedQName
from mech.fusion.avm2.interfaces import IMultiname

from zope.interface import implementer
from zope.component import adapter, provideAdapter

class Node(object):
    def get_name(self):
        pass

    def dependencies(self):
        pass

    def render(self, ilasm):
        pass

class ClassNodeBase(Node):
    def get_fields(self):
        pass

    def get_base_class(self):
        pass

    def render(self, ilasm):
        ilasm.begin_class(IMultiname(self), self.get_base_class())
        for f_name, (f_type, f_default) in self.get_fields():
            cts_type = self.cts.lltype_to_cts(f_type)
            f_name = self.cts.escape_name(f_name)
            if cts_type != types.types.void:
                slot = AbcSlotTrait(IMultiname(f_name), IMultiname(cts_type))
                ilasm.context.add_instance_trait(slot)

        self.render_ctor(ilasm)
        self.render_toString(ilasm)
        self.render_methods(ilasm)
        ilasm.exit_context()

    def render_ctor(self, ilasm):
        pass

    def render_toString(self, ilasm):
        pass

    def render_methods(self, ilasm):
        pass


@implementer(IMultiname)
@adapter(ClassNodeBase)
def _adapter(self):
    return IMultiname(self.get_type())

provideAdapter(_adapter)
