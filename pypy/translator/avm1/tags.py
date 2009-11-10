
import struct

from pypy.translator.avm1.records import RecordHeader, ShapeWithStyle, Matrix, CXForm
from pypy.translator.avm1.avm1 import Block
from pypy.translator.avm1.util import BitStream
from pypy.translator.avm2.abc_ import AbcFile

class SwfTag(object):

    TAG_TYPE = -1
    TAG_MIN_VERSION = -1

    def serialize_data(self):
        return ""
    
    def serialize(self):
        data = self.serialize_data()
        return RecordHeader(self.TAG_TYPE, len(data)).serialize().serialize(endianness="<") + data

class SetBackgroundColor(SwfTag):
    
    TAG_TYPE = 9
    TAG_MIN_VERSION = 1

    def __init__(self, color):
        self.color = color

    def serialize_data(self):
        return struct.pack("<HB", (self.color >> 8) & 0xFFFF, self.color & 0xFF)

class DoAction(SwfTag, Block):

    TAG_TYPE = 12
    TAG_MIN_VERSION = 3

    def __init__(self):
        Block.__init__(self, None, True)

    def serialize_data(self):
        return Block.serialize(self)

class DoABC(SwfTag, AbcFile):

    TAG_TYPE = 82
    TAG_MIN_VERSION = 9

    def __init__(self, name="PyPy", flags=0):
        AbcFile.__init__(self)
        self.name  = name
        self.flags = flags
    
    def serialize_data(self):
        return struct.pack("<L", self.flags) + self.name + "\0" + AbcFile.serialize(self)

class SymbolClass(SwfTag):

    TAG_TYPE = 76
    TAG_MIN_VERSION = 9

    def __init__(self, symbols):
        self.symbols = symbols

    def serialize_data(self):
        code = struct.pack("<H", len(self.symbols))
        for char_id, classname in self.symbols.iteritems():
            c = struct.pack("<H", char_id)
            code += struct.pack("<H", char_id)
            code += classname + "\0"
        return code

class DefineShape(SwfTag):

    TAG_TYPE = 2
    TAG_MIN_VERSION = 1
    TAG_VARIANT = 1
    
    _current_variant = None
    
    def __init__(self, shapes=None, characterid=None):
        self.shapes = ShapeWithStyle() if shapes is None else shapes
        self.characterid = shapeid

    def serialize_data(self):
        self.shapes.calculate_bounds()
        DefineShape._current_variant = self.TAG_VARIANT
        bytes = struct.pack("<H", self.shapeid) + (self.shapes.shape_bounds.serialize() + self.shapes.serialize()).serialize()
        DefineShape._current_variant = None
        return bytes

class DefineShape2(DefineShape):
    TAG_TYPE = 22
    TAG_MIN_VERSION = 2
    TAG_VARIANT = 2

class DefineShape3(DefineShape):
    TAG_TYPE = 32
    TAG_MIN_VERSION = 32
    TAG_VARIANT = 3

class DefineShape4(DefineShape):
    
    TAG_TYPE = 83
    TAG_MIN_VERSION = 8
    TAG_VARIANT = 4

    def serialize_data(self):
        self.shapes.calculate_bounds()
        DefineShape._current_variant = 4
        shapeidshort = struct.pack("<H", self.shapeid)  # Shape ID
        bits =  (self.shapes.shape_bounds.serialize() + # ShapeBounds Rect
                 self.shapes.edge_bounds.serialize())   # EdgeBounds Rect
        
        bits.zero_fill(6) # Reserved

        bits.write_bit(self.shapes.has_scaling)     # UsesNonScalingStrokes
        bits.write_bit(self.shapes.has_non_scaling) # UsesScalingStrokes
        
        bits += self.shapes.serialize() # ShapeWithStyle
        
        DefineShape._current_variant = None

        return shapeidshort + bits.serialize()

class ShowFrame(SwfTag):
    TAG_TYPE = 1
    TAG_MIN_VERSION = 1

class FileAttributes(SwfTag):
    
    TAG_TYPE = 69
    TAG_MIN_VERSION = 1
    
    def __init__(self, hasMetadata=False, useAS3=True, useNetwork=False):
        """
        Constructor.
        @param hasMetadata	True if the SWF contains a metadata tag.
        @param useAS3		True if the SWF uses ActionScript 3.0.
        @param useNetwork	If true the SWF is given network access when
                                loaded locally.  If false the SWF is given local access.
        """
        self.hasMetadata = hasMetadata
        self.useAS3      = useAS3
        self.useNetwork  = useNetwork

    def serialize_data(self):
        bits = BitStream()
        bits.zero_fill(3)
        bits.write_bit(self.hasMetadata)
        bits.write_bit(self.useAS3)
        bits.zero_fill(2)
        bits.write_bit(self.useNetwork)
        bits.zero_fill(24)

        return bits.serialize()
    
class PlaceObject(SwfTag):
    
    TAG_TYPE = 4
    TAG_MIN_VERSION = 1

    def __init__(self, shapeid, depth, transform=None, colortransform=None):
        self.shapeid = shapeid
        self.depth = depth
        self.transform = transform or Matrix()
        self.colortransform = colortransform or CXForm()

    def serialize_data(self):
        return (struct.pack("<HH", self.shapeid, self.depth) +
                (self.transform.serialize() + self.colortransform.serialize()).serialize())

class PlaceObject2(PlaceObject):

    TAG_TYPE = 26
    TAG_MIN_VERSION = 3

    def __init__(self, shapeid, depth, name=None, transform=None, colortransform=None):
        self.shapeid = shapeid
        self.depth = depth
        self.name = name
        self.transform = transform
        self.colortransform = colortransform
    
    def serialize_data(self):
        flags = BitStream()
        flags.write_bit(False) # HasClipActions
        flags.write_bit(False) # HasClipDepth
        flags.write_bit(self.name is not None) # HasName
        flags.write_bit(False) # HasRatio
        flags.write_bit(self.colortransform is not None)
        flags.write_bit(self.transform is not None)
        flags.write_bit(True)  # HasCharacter
        flags.write_bit(False) # FlagMove
        
        bytes = flags.serialize() + struct.pack("<HH", self.depth, self.shapeid)
        bits = BitStream()
        if self.name is not None:
            bytes += self.name + "\0"
        if self.transform is not None:
            bits += self.transform.serialize()
        if self.colortransform is not None:
            bits += self.colortransform.serialize()
        return bytes + bits.serialize()

class DefineEditText(SwfTag):

    TAG_TYPE = 37
    TAG_MIN_VERSION = 4
    
    def __init__(self, rect, variable, text="", readonly=True, isHTML=False,
                 wordwrap=False, multiline=True, password=False, autosize=True,
                 selectable=True, border=False, color=None, maxlength=None,
                 layout=None, font=None, size=12, fontclass=None, characterid=None):
        
        self.rect        = rect
        self.variable    = variable
        self.text        = text
        self.readonly    = readonly
        self.isHTML      = isHTML
        self.wordwrap    = wordwrap
        self.multiline   = multiline
        self.password    = password
        self.autosize    = autosize
        self.selectable  = selectable
        self.border      = border
        self.color       = color
        self.maxlength   = maxlength
        self.layout      = layout
        self.font        = font
        self.size        = size
        self.fontclass   = fontclass
        self.characterid = characterid

        self.outlines    = False
        self.wasstatic   = False

    def serialize_data(self):
        bits = self.rect.serialize()
        bits.flush()
        bits.write_bit(self.text != "")
        bits.write_bit(self.wordwrap)
        bits.write_bit(self.multiline)
        bits.write_bit(self.password)
        bits.write_bit(self.readonly)
        bits.write_bit(self.color is not None)
        bits.write_bit(self.maxlength is not None)
        bits.write_bit(self.font is not None)
        bits.write_bit(self.fontclass is not None)
        bits.write_bit(self.autosize)
        bits.write_bit(self.layout is not None)
        bits.write_bit(not self.selectable)
        bits.write_bit(self.border)
        bits.write_bit(self.wasstatic)
        bits.write_bit(self.isHTML)
        bits.write_bit(self.outlines)
        
        bytes = struct.pack("<H", self.characterid) + bits.serialize()
        if self.font is not None:
            bytes += struct.pack("<H", self.font.id) # Doesn't exist yet.
        if self.fontclass is not None:
            bytes += self.fontclass + "\0"
        if self.font is not None:
            bytes += struct.pack("<H", self.size * 20)
            
        if self.color is not None:
            bytes += self.color.serialize().serialize()
        if self.maxlength is not None:
            bytes += struct.pack("<H", self.maxlength)
        if self.layout is not None:
            bytes += self.layout.serialize() # Doesn't exist yet.

        bytes += self.variable + "\0"

        if self.text != "":
            bytes += self.text + "\0"

        return bytes
        
class End(SwfTag):

    TAG_TYPE = 0
    TAG_MIN_VERSION = 0

    def __call__(self):
        return self
    
    def serialize(self):
        return "\0\0"

End = End()

