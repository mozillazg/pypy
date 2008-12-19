

from pypy.translator.avm.swf import SwfData
from pypy.translator.avm.tags import DoAction, SetBackgroundColor

def create_assembler(name):
    return AsmGen(name, DoAction())

def bootstrap_avm1(asmgen):
    data = SwfData()
    data.add_tag(SetBackgroundColor(0x333333))
    data.add_tag(asmgen)
    return data.serialize()
