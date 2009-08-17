
import struct

def serialize_u32(value):
    s = ""
    i = 0
    while True:
        i += 1
        if i == 5:
            raise ValueError, "value does not fit in a u32"
        bits = value & 0b01111111 # low 7 bits
        value >>= 7
        if not value:
            s += chr(bits)
            break
        s += chr(0b10000000 | bits)
    return s

def serialize_s24(value):
    m = struct.pack("<l", value)
    if (value < 0 and m[3] != "\xff") or (value >= 0 and m[3] != "\x00"):
        raise ValueError, "value does not fit in a s24"
    return m[:3]

Avm2Backpatch = namedtuple("Avm2Backpatch", "location base lbl")

class Avm2Label(object):
    _next_label = 1000

    def __init__(self, asm, address=-1):
        self.asm = asm
        self.name = Avm2Label._next_label
        Avm2Label._next_label += 1
        self.address = address
        self.stack_depth = asm._stack_depth_max
        self.scope_depth = asm._scope_depth_max
        
    def write_relative_offset(self, base, location):
        if self.address == -1:
            self.asm.add_backpatch(Avm2Backpatch(location, base, self))
            return "\0\0\0"
        else:
            return serialize_s24(self.address - base)

    def __repr__(self):
        return "<Avm2Label (name=%d, address=%d, stack_depth=%d, scope_depth=%d)>" \
            % (self.name, self.address, self.stack_depth, self.scope_depth)
