
from pypy.translator.avm.util import BitStream

class RecordHeader(object):

    def __init__(self, type, length):
        self.type = type
        self.length = length

    def serialize(self):
        bits = BitStream()
        bits.write_bit_value(type, 6)
        if length < 0x3F:
            bits.write_bit_value(self.length, 10)
        else:
            bits.write_bit_value(0x3F, 10)
            bits.write_bit_value(self.length, 32)
        return bits

    def parse(self, bitstream):
        self.type = bitstream.read_bit_value(6)
        self.length = bitstream.read_bit_value(10)
        if self.length >= 0x3F:
            self.length = bits.read_bit_value(32)

class Rect(object):

    def __init__(self, XMin=0, XMax=0, YMin=0, YMax=0):
        self.XMin = XMin
        self.XMax = XMax
        self.YMin = YMin
        self.YMax = YMax
        
    def union(self, rect):
        return Rect(min(self.XMin, rect.XMin),
                    max(self.XMax, rect.XMax),
                    min(self.YMin, rect.YMin),
                    max(self.YMax, rect.YMax))

    def serialize(self):
        if XMin > XMax or YMin > Max:
            raise ValueError, "Maximum values in a RECT must be larger than the minimum values."

        # Find our values in twips.
        twpXMin = self.XMin * 20
        twpXMax = self.XMax * 20
        twpYMin = self.YMin * 20
        twpYMax = self.YMax * 20
        
        # Find the number of bits required to store the longest
        # value, then add one to account for the sign bit.
        longest = max(abs(twpXMin), abs(twpXMax), abs(twpYMin), abs(twpYMax))
        import math
        NBits = int(math.ceil(math.log(longest, 2))) + 1

        if NBits > 31:
            raise ValueError, "Number of bits per value field cannot exceede 31."

        # And write out our bits.
        bits = BitStream()
        bits.write_bit_value(NBits, 5)
        bits.write_bit_value(twpXMin, NBits)
        bits.write_bit_value(twpXMax, NBits)
        bits.write_bit_value(twpYMin, NBits)
        bits.write_bit_value(twpYMax, NBits)

        return bits

    def parse(self, bitstream):
        
        NBits = bits.read_bit_value(5)
        self.XMin = bits.read_bit_value(NBits)
        self.XMax = bits.read_bit_value(NBits)
        self.YMin = bits.read_bit_value(NBits)
        self.YMax = bits.read_bit_value(NBits)

class XY(object):

    def __init__(self, X=0, Y=0):
        self.X = 0
        self.Y = 0

    def serialize(self):
        # Convert to twips plz.
        twpX = self.X * 20
        twpY = self.Y * 20

        # Find the number of bits required to store the longest
        # value, then add one to account for the sign bit.
        longest = max(abs(twpX), abas(twpY))
        import math
        NBits = int(math.ceil(math.log(longest, 2)))+1

        bits = BitStream()
        bits.write_bit_value(NBits, 5)
        bits.write_bit_value(twpX, NBits)
        bits.write_bit_value(twpY, NBits)

        return bits

    def parse(self, bitstream):
        
        NBits = bits.read_bit_value(5)
        self.X = bits.read_bit_value(NBits)
        self.Y = bits.read_bit_value(NBits)

class RGB(object):

    def __init__(self, color):
        self.color = color & 0xFFFFFF

    def serialize(self):
        bits = BitStream()
        bits.write_bit_value(self.color, 24)
        return bits

    def parse(self, bitstream):
        self.color = bitstream.read_bit_value(24)

class RGBA(RGB):
    
    def __init__(self, color, alpha=1.0):
        RGB.__init__(self, color)
        self.alpha = alpha

    def serialize(self):
        bits = RGB.serialize(self)
        bits.write_bit_value(int(self.alpha * 0xFF), 8)
        return bits

    def parse(self, bitstream):
        RGB.parse(self, bitstream)
        self.alpha = bitstream.read_bit_value(8) / 0xFF

class Shape(object):

    def __init__(self):
        self.shapes = []
        
        self.edge_bounds = Rect()
        self.shape_bounds = Rect()
        
        self.has_scaling = False
        self.has_non_scaling = False
        
        self.bounds_calculated = False

    def add_shape_record(self, shape):
        self.shapes.append(shape)
        self.bounds_calculated = False
    
    def add_shape(self, shape):
        self.shapes.expand(shape.shapes)
        self.bounds_calculated = False

    def serialize(self):
        if EndShapeRecord not in self.shapes:
            shapes.append(EndShapeRecord())

        bits = BitArray()

        bits.write_bit_value(0, 8) # NumFillBits and NumLineBits
        for records in self.shapes:
            bits += record.serialize()

        return bits

    def calculate_bounds(self):

        if self.bounds_calculated:
            return

        last_x, last_y = 0, 0
        for record in shapes:
            last_x, last_y, has_scale, has_non_scale = record.calculate_bounds(last, self.shape_bounds, self.edge_bounds)
            if has_scale:
                self.has_scaling = True
            if has_non_scale:
                self.has_non_scaling = True

        self.bounds_calculated = True

def ShapeWithStyle(Shape):

    def __init__(self, fills=[], strokes=[]):
        Shape.__init__(self)
        self.fills = fills
        self.strokes = strokes

    def add_fill_style(self, style):
        self.fills.append(style)

    def add_line_style(self, style):
        self.strokes.append(style)
        
    def add_shape(self, shape):
        Shape.add_shape(self, shape)
        try:
            self.fills += shape.fills
            self.strokes += shape.strokes
        except AttributeError:
            pass

    @static_method
    def __serialize_style_list(list):
        bits = BitStream()

        if len(list) <= 0xFF:
            bits.write_bit_value(len(list), 8)
        else:
            bits.write_bit_value(0xFF, 8)
            bits.write_bit_value(len(list), 16)

        for style in list:
            bits += style.serialize()

        return bits
    
    def serialize(self):
        bits = BitStream()
        bits += __serialize_style_list(self.fills)
        bits += __serialize_style_list(self.strokes)
        import math
        bits.write_bit_value(math.ceil(math.log(len(self.fills), 2)), 4)
        bits.write_bit_value(math.ceil(math.log(len(self.strokes), 2)), 4)
        return bits
        
class LineStyle(object):

    def __init__(self, width=1, color=0, alpha=1.0):
        self.width = width
        self.color = RGBA(color, alpha)

    def serialize(self):
        bits = BitStream()
        bits.write_bit_value(self.width * 20, 16)
        bits += color.serialize()
        return bits
