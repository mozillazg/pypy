
from pypy.translator.avm.util import BitStream
from pypy.translator.avm.avm1 import Block

class SwfTag(object):

    TAG_TYPE = -1
    TAG_MIN_VERSION = -1

    def serialize_data(self):
        return ""
    
    def serialize(self):
        data = self.serialize_data(self)
        return RecordHeader(self.TAG_TYPE, len(data)).serialize().serialize() + data

class SetBackgroundColor(SwfTag):
    
    TAG_TYPE = 9
    TAG_MIN_VERSION = 1

    def __init__(self, color):
        self.color = color

    def serialize_data(self):
        import struct
        return struct.pack("LB", color >> 8 & 0xFFFF, color & 0xFF)

class DoAction(SwfTag, Block):

    TAG_TYPE = 12
    TAG_MIN_VERSION = 3

    def __init__(self):
        Block.__init__(self, True)

    def serialize_data(self):
        return Block.serialize(self)

class End(SwfTag):

    TAG_TYPE = 0
    TAG_MIN_VERSION = 0
    
    def serialize(self):
        return "\0\0"
