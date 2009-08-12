
from pypy.translator.avm.util import BitStream
from math import log, ceil, sqrt

def serialize_style_list(lst):
    bits = BitStream()

    if len(lst) <= 0xFF:
        bits.write_bit_value(len(lst), 8)
    else:
        bits.write_bit_value(0xFF, 8)
        bits.write_bit_value(len(lst), 16)

    for style in lst:
        bits += style.serialize()

    return bits

def nbits(n, *a):
    return int(ceil(log(max(1, n, *a), 2)))

def nbits_abs(n, *a):
    return nbits(abs(n), *(abs(n) for n in a))

def style_list_bits(lst):
    return nbits(len(lst))

def clamp(n, minimum, maximum):
    return max(minimum, min(n, maximum))

class RecordHeader(object):

    def __init__(self, type, length):
        self.type = type
        self.length = length

    def serialize(self):
        bits = BitStream()
        bits.write_int_value(self.type, 10)
        if self.length < 0x3F:
            bits.write_int_value(self.length, 6)
        else:
            bits.write_int_value(0x3F, 6)
            bits.write_int_value(self.length, 32)
        return bits

    def parse(self, bitstream):
        self.type = bitstream.read_bit_value(10)
        self.length = bitstream.read_bit_value(6)
        if self.length >= 0x3F:
            self.length = bitstream.read_bit_value(32)

class _EndShapeRecord(object):
    
    def __call__(self, *a, **b):
        pass

    def serialize(self):
        bitstream = BitStream()
        bitstream.zero_fill(6)
        return bitstream

EndShapeRecord = _EndShapeRecord()

class Rect(object):

    def __init__(self, XMin=0, XMax=0, YMin=0, YMax=0):
        self.XMin = XMin
        self.XMax = XMax
        self.YMin = YMin
        self.YMax = YMax
        
    def union(self, rect, *rects):
        r = Rect(min(self.XMin, rect.XMin),
                 max(self.XMax, rect.XMax),
                 min(self.YMin, rect.YMin),
                 max(self.YMax, rect.YMax))
        if len(rects) > 0:
            return r.union(*rects)
        return r
    
    def serialize(self):
        if self.XMin > self.XMax or self.YMin > self.YMax:
            raise ValueError, "Maximum values in a RECT must be larger than the minimum values."

        # Find our values in twips.
        twpXMin = self.XMin * 20
        twpXMax = self.XMax * 20
        twpYMin = self.YMin * 20
        twpYMax = self.YMax * 20
        
        # Find the number of bits required to store the longest
        # value, then add one to account for the sign bit.
        NBits = nbits_abs(twpXMin, twpXMax, twpYMin, twpYMax)+1

        if NBits > 31:
            raise ValueError, "Number of bits per value field cannot exceede 31."

        # And write out our bits.
        bits = BitStream()
        bits.write_int_value(NBits, 5)
        bits.write_int_value(twpXMin, NBits)
        bits.write_int_value(twpXMax, NBits)
        bits.write_int_value(twpYMin, NBits)
        bits.write_int_value(twpYMax, NBits)

        return bits

    def parse(self, bitstream):
        
        NBits = bitstream.read_bit_value(5)
        self.XMin = bitstream.read_bit_value(NBits)
        self.XMax = bitstream.read_bit_value(NBits)
        self.YMin = bitstream.read_bit_value(NBits)
        self.YMax = bitstream.read_bit_value(NBits)

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
        NBits = nbits_abs(twpX, twpY)

        bits = BitStream()
        bits.write_int_value(NBits, 5)
        bits.write_int_value(twpX, NBits)
        bits.write_int_value(twpY, NBits)

        return bits

    def parse(self, bitstream):
        
        NBits = bitstream.read_bit_value(5)
        self.X = bitstream.read_bit_value(NBits)
        self.Y = bitstream.read_bit_value(NBits)

class RGB(object):

    def __init__(self, color):
        self.color = color & 0xFFFFFF

    def serialize(self):
        bits = BitStream()
        bits.write_int_value(self.color, 24)
        return bits

    def parse(self, bitstream):
        self.color = bitstream.read_bit_value(24)

class RGBA(RGB):
    
    def __init__(self, color, alpha=1.0):
        super(RGBA, self).__init__(color)
        self.alpha = alpha

    def serialize(self):
        bits = RGB.serialize(self)
        
        from pypy.translator.avm.tags import DefineShape
        
        # If we are in a DefineShape and the version does not support
        # alpha (DefineShape1 or DefineShape2), don't use alpha!
        if DefineShape._current_variant not in (1, 2):
            bits.write_int_value(int(self.alpha * 0xFF), 8)
        
        return bits

    def parse(self, bitstream):
        RGB.parse(self, bitstream)
        self.alpha = bitstream.read_bit_value(8) / 0xFF

class CXForm(object):
    has_alpha = False
    def __init__(self, rmul=1, gmul=1, bmul=1, radd=0, gadd=0, badd=0):
        self.rmul = rmul
        self.gmul = gmul
        self.bmul = bmul
        self.amul = 1
        self.radd = radd
        self.gadd = gadd
        self.badd = badd
        self.aadd = 0

    def serialize(self):
        has_add_terms = self.radd != 0 or self.gadd != 0 or self.badd != 0 or self.aadd != 0
        has_mul_terms = self.rmul != 1 or self.gmul != 1 or self.bmul != 1 or self.amul != 1
        
        rm = abs(self.rmul * 256)
        gm = abs(self.gmul * 256)
        bm = abs(self.bmul * 256)
        am = abs(self.amul * 256)
        
        ro = clamp(self.radd, -255, 255)
        go = clamp(self.gadd, -255, 255)
        bo = clamp(self.badd, -255, 255)
        ao = clamp(self.aadd, -225, 255)
        
        NBits = 0
        if has_mul_terms: NBits = nbits_abs(rm, gm, bm, am)
        if has_add_terms: NBits = max(NBits, nbits_abs(ro, go, bo, ao))
        
        bits = BitStream()
        bits.write_int_value(NBits, 4)

        if has_mul_terms:
            bits.write_int_value(rm, NBits)
            bits.write_int_value(gm, NBits)
            bits.write_int_value(bm, NBits)
            if self.has_alpha: bits.write_int_value(am, NBits)

        if has_add_terms:
            bits.write_int_value(ro, NBits)
            bits.write_int_value(go, NBits)
            bits.write_int_value(bo, NBits)
            if self.has_alpha: bits.write_int_value(ao, NBits)

        return bits

class CXFormWithAlpha(CXForm):
    has_alpha = True
    def __init__(self, rmul=1, gmul=1, bmul=1, amul=1, radd=0, gadd=0, badd=0, aadd=0):
        super(self, CXFormWithAlpha).__init__(rmul, gmul, bmul, radd, gadd, badd)
        self.amul = amul
        self.aadd = aadd

class Matrix(object):
    
    def __init__(self, a=1, b=0, c=0, d=1, tx=0, ty=0):
        self.a, self.b, self.c, self.d, self.tx, self.ty = a, b, c, d, tx, ty

    def serialize(self):
        
        def write_prefixed_values(a, b):
            NBits = nbits(a, b)
            bits.write_int_value(NBits, 5)
            bits.write_int_value(a, NBits)
            bits.write_int_value(b, NBits)
        
        bits = BitStream()
        if self.a != 1 or self.d != 1: # HasScale
            bits.write_bit(True)
            write_prefixed_values(self.a, self.d)
        else:
            bits.write_bit(False)

        if self.b != 0 or self.c != 0: # HasRotate
            bits.write_bit(True)
            write_prefixed_values(self.b, self.c)
        else:
            bits.write_bit(False)

        write_prefixed_values(self.tx * 20, self.ty * 20)
        return bits

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
            self.shapes.append(EndShapeRecord())

        bits = BitStream()

        bits.write_int_value(0, 8) # NumFillBits and NumLineBits
        for record in self.shapes:
            bits += record.serialize()

        return bits

    def calculate_bounds(self):

        if self.bounds_calculated:
            return

        last = 0, 0
        style = None
        for record in self.shapes:
            last, (self.shape_bounds, self.edge_bounds), (has_scale, has_non_scale, style) = \
                  record.calculate_bounds(last, self.shape_bounds, self.edge_bounds, style)
            if has_scale:
                self.has_scaling = True
            if has_non_scale:
                self.has_non_scaling = True

        self.bounds_calculated = True

class ShapeWithStyle(Shape):

    def __init__(self, fills=None, strokes=None):
        super(self, ShapeWithStyle).__init__(self)
        self.fills = fills or []
        self.strokes = strokes or []

    def add_fill_style(self, style):
        style.parent = self.fills
        self.fills.append(style)

    def add_line_style(self, style):
        style.parent = self.strokes
        self.strokes.append(style)
        
    def add_shape(self, shape):
        Shape.add_shape(self, shape)
        try:
            self.fills += shape.fills
            self.strokes += shape.strokes
        except AttributeError:
            pass
    
    def serialize(self):
        bits = BitStream()
        bits += serialize_style_list(self.fills)
        bits += serialize_style_list(self.strokes)
        bits.write_int_value(style_list_bits(self.fills), 4)
        bits.write_int_value(style_list_bits(self.strokes), 4)
        return bits

class LineStyle(object):

    caps = "round"
    
    def __init__(self, width=1, color=0, alpha=1.0):
        self.width = width
        self.color = RGBA(color, alpha)

    @property
    def index(self):
        return self.parent.find(self)
    
    def serialize(self):
        bits = BitStream()
        bits.write_int_value(self.width * 20, 16)
        bits += self.color.serialize()
        return bits

class LineStyle2(LineStyle):

    def __init__(self, width=1, fillstyle=None, pixel_hinting=False, scale_mode=None, caps="round", joints="round", miter_limit=3):

        color, alpha, self.fillstyle = 0, 1.0, None
        
        if isinstance(fillstyle, RGBA):
            color = fillstyle.color
            alpha = fillstyle.alpha
        elif isinstance(fillstyle, RGB):
            color = fillstyle.color
        elif isinstance(fillstyle, int):
            if fillstyle > 0xFFFFFF:
                color = fillstyle & 0xFFFFFF
                alpha = fillstyle >> 6 & 0xFF
            else:
                color = fillstyle
        elif isinstance(fillstyle, FillStyleSolidFill):
            color = fillstyle.color.color
            alpha = fillstyle.color.alpha
        elif isinstance(fillstyle, FillStyle):
            self.fillstyle = fillstyle
        
        super(self, LineStyle2).__init__(self, width, color, alpha)
        self.pixel_hinting = pixel_hinting
        self.h_scale = (scale_mode == "normal" or scale_mode == "horizontal")
        self.v_scale = (scale_mode == "normal" or scale_mode == "vertical")

        if caps == "square":  self.caps = 2
        elif caps == None:    self.caps = 1
        elif caps == "round": self.caps = 0
        else:
            raise ValueError, "Invalid cap style '%s'." % caps

        if joints == "miter":   self.joints = 2
        elif joints == "bevel": self.joints = 1
        elif joints == "round": self.joints = 0

        self.miter_limit = miter_limit

    def serialize(self):

        bits = BitStream()
        bits.write_int_value(self.width * 20, 8)
        bits.write_int_value(self.width * 20 >> 8, 8)

        bits.write_int_value(self.caps, 2)
        bits.write_int_value(self.joints, 2)
        bits.write_bit(self.fillstyle is not None);
        bits.write_bit(self.h_scale)
        bits.write_bit(self.v_scale)
        bits.write_bit(self.pixel_hinting)

        if self.joints == 2:
            bits.write_fixed_value(self.miter_limit, 16, True)

        if self.fillstyle:
            bits.write_bits(self.fillstyle.serialize())
        else:
            bits.write_bits(self.color.serialize())

        return bits

    def cap_style_logic(self, style, last, delta):
        # Half thickness (radius of round cap; diameter is thickness)
        off = style.width / 2.0
        dx, dy = delta
        lx, ly = last
        
        if style.caps == "round":
            r = Rect()
            r.XMin = cmp(dx, 0) * off
            r.YMin = cmp(dy, 0) * off
            r.XMax = r.XMin + dx
            r.YMax = r.XMax + dy
            return r
        
        if style.caps == "square":
            
            # Account for the length of the caps.
            dellen = sqrt(dx*dx + dy*dy)  # Delta length
            norm = (dellen+off*2)/dellen  # Extra length
            dx *= norm                    # Add the extra length
            dy *= norm
            sqx, sqy = delta              # Square cap offset
            norm = off/dellen             # Offset amount
            sqx *= norm                   # Position offsets.
            sqy *= norm
            
            # And offset the position.
            lx -= sqx
            ly -= sqy

        # Right-hand normal to vector delta relative to (0, 0).
        p1x, p1y = (-dy, dx)
        norm = sqrt(p1x*p1x + p1y*p1y)
        p1x /= norm
        p1y /= norm

        # Left-hand normal to vector delta relative to (0, 0)
        p2x, p2y = (-p1x, -p1y)
        
        # Right-hand normal to vector delta relative to delta.
        p3x, p3y = (p1x + dx, p1y + dy)

        # Left-hand normal to vector delta relative to delta.
        p4x, p4y = (p2x + dx, p2y + dy)

        return Rect(
            min(p1x, p2x, p3x, p4x) + lx,
            max(p1x, p2x, p3x, p4x) + lx,
            min(p1y, p2y, p3y, p4y) + ly,
            max(p1y, p2y, p3y, p4y) + ly)

class FillStyle(object):

    TYPE = -1
    
    @property
    def index(self):
        return self.parent.find(self)
    
    def serialize(self):
        bits = BitStream()
        bits.write_int_value(self.TYPE, 8)
        bits += self.serialize_inner()
        return bits

class FillStyleSolidFill(object):
    
    def __init_(self, color, alpha=1.0):
        self.color = RGBA(color, alpha)

    def serialize_inner(self):
        return self.color.serialize()

class GradRecord(object):

    def __init__(self, ratio, color, alpha=1.0):
        self.ratio = ratio
        self.color = RGBA(color, alpha)

    def serialize(self):
        bits = BitStream()
        bits.write_int_value(self.ratio, 8)
        bits += self.color.serialize()
        return bits

class Gradient(object):

    def __init__(self, grads, spread="pad", interpolation="rgb", focalpoint=0):
        import operator
        grads.sort(key=operator.attrgetter("ratio"))
        self.grads = grads
        self.spread = spread
        self.interpolation = interpolation
        self.focalpoint = focalpoint
        
    @classmethod
    def from_begin_gradient_fill(cls, colors, alphas, ratios, spread, interpolation, focalpoint):
        grads = [GradRecord(*t) for t in zip(ratios, colors, alphas)]
        return cls(grads, spread, interpolation, focalpoint)
    
class StraightEdgeRecord(object):

    def __init__(self, delta_x, delta_y):
        self.delta_x = delta_x
        self.delta_y = delta_y
        self.bounds_calculated = False

    def serialize(self):
            
        bits = BitStream()
        
        if self.delta_x == 0 and self.delta_y == 0:
            return bits

        bits.write_bit(True) # TypeFlag
        bits.write_bit(True) # StraightFlag

        X = self.delta_x * 20
        Y = self.delta_y * 20

        NBits = nbits_abs(X, Y)

        if NBits > 15:
            raise ValueError("Number of bits per value field cannot exceed 15")
        
        bits.write_int_value(NBits, 4)
        NBits += 2
        if X == 0:
            # Vertical Line
            bits.write_bit(False) # GeneralLineFlag
            bits.write_bit(True)  # VerticalLineFlag
            bits.write_int_value(Y, NBits)
        elif Y == 0:
            # Horizontal Line
            bits.write_bit(False) # GeneralLineFlag
            bits.write_bit(True)  # HorizontalLineFlag
            bits.write_int_value(X, NBits)
        else:
            # General Line
            bits.write_bit(True) # GeneralLineFlag
            bits.write_int_value(X, NBits)
            bits.write_int_value(Y, NBits)

        return bits

    def calculate_bounds(self, last, shape_bounds, edge_bounds, style):
        rect = Rect(last[0], last[1], self.delta_x, self.delta_y)
        return ((self.delta_x, self.delta_y),
                (shape_bounds.union(rect),
                 edge_bounds.union(LineStyle2.cap_style_logic(style,
                              last, (self.delta_x, self.delta_y)))),
                (False, False, style))


class CurvedEdgeRecord(object):

    def __init__(self, controlx, controly, anchorx, anchory):
        self.controlx = controlx
        self.controly = controly
        self.anchorx = anchorx
        self.anchory = anchory

    def serialize(self):
            
        bits = BitStream()
        
        if self.delta_x == 0 and self.delta_y == 0:
            return bits

        bits.write_bit(True)  # TypeFlag
        bits.write_bit(False) # StraightFlag

        cX = self.controlx * 20
        cY = self.controly * 20
        aX = self.anchorx  * 20
        aY = self.anchory  * 20
        
        NBits = nbits_abs(cX, cY, aX, aY)

        if NBits > 15:
            raise ValueError("Number of bits per value field cannot exceed 15")

        bits.write_int_value(NBits, 4)
        NBits += 2
        bits.write_int_value(cX, NBits)
        bits.write_int_value(cY, NBits)
        bits.write_int_value(aX, NBits)
        bits.write_int_value(aY, NBits)
        return bits
    
    def _get_x(self, t):
        return self.controlx * 2 * (1-t) * t + self.anchorx * t * t;

    def _get_y(self, t):
        return self.controly * 2 * (1-t) * t + self.anchory * t * t;

    def _get_p(self, t):
        return (self._get_x(t), self._get_y(t))
    
    def calculate_bounds(self, last, shape_bounds, edge_bounds, style):
        union = Rect(0, 0, 0, 0)
        # CurvedEdgeRecord Bounds
        # Formulas somewhat based on
        # http://code.google.com/p/bezier/source/browse/trunk/bezier/src/flash/geom/Bezier.as
        # Maths here may be incorrect
        
        # extremumX = last.x - 2 * control.x + anchor.x
        # extremumX = last.x - 2 * ( controlDeltaX - last.x ) + anchorDeltaX - last.x
        # extremumX = (last.x - last.x) - 2 * ( controlDeltaX - last.x ) + anchorDeltaX
	# extremumX = -2 * ( controlDeltaX - last.x ) + anchorDeltaX
        
	# For the case of last.[x/y] = 0, we can use the formula below.

        x = -2 * self.controlx + self.anchorx
        t = -self.controlx / x
        p = self._get_x(t)

        if t <= 0 or t >= 1:
            union.XMin = last[0] + min(self.anchorx, 0)
            union.XMax = union.XMin + max(self.anchorx, 0)
        else:
            union.XMin = min(p, 0, self.anchorx + last[0])
            union.XMax = union.XMin + max(p - last[0], 0, self.anchorx)
            
        y = -2 * self.controly + self.anchory
        t = -self.controly / y
        p = self._get_y(t)

        if t <= 0 or t >= 1:
            union.YMin = last[1] + min(self.anchory, 0)
            union.YMax = union.YMin + max(self.anchory, 0)
        else:
            union.YMin = min(p, 0, self.anchory + last[1])
            union.YMax = union.YMin + max(p - last[0], 0, self.anchorY)

        # CapStyle logic:

        # Assume that p0 is last (start anchor),
        # p1 is control, and p2 is (end) anchor.

        # Get some small increments in the segment to
        # find somewhat of a slope derivative type thing.

        # We should be able to pass these two line deltas
        # into LineStyle2.cap_style_logic and union the
        # results.
        
        slope1 = self._get_p(0.01)
        slope2 = (self.anchorx - self._get_x(0.99), self.anchory - self._get_y(0.99))
        end_cap_rect   = LineStyle2.cap_style_logic(style, last, slope2)
        start_cap_rect = LineStyle2.cap_style_logic(style, last, slope1)

        return ((self.anchorx, self.anchory),
                (shape_bounds.union(union),
                 edge_bounds.union(union, start_cap_rect, end_cap_rect)),
                (False, False, style))

class StyleChangeRecord(object):

    def __init__(self, delta_x, delta_y, linestyle=None,
                 fillstyle0=None, fillstyle1=None,
                 fillstyles=None, linestyles=None):
        
        self.delta_x = delta_x
        self.delta_y = delta_y
        self.linestyle = linestyle
        self.fillstyle0 = fillstyle0
        self.fillstyle1 = fillstyle1
        self.fillstyles = fillstyles
        self.linestyles = linestyles

    def serialize(self):
        bits = BitStream()
        if self.fillstyle0 is not None and self.fillstyle1 is not None and \
               self.fillstyle0.parent != self.fillstyle1.parent:
            raise ValueError("fillstyle0 and fillstyle1 do not have the same parent!")
        
        fsi0 = 0 if self.fillstyle0 is None else self.fillstyle0.index
        fsi1 = 0 if self.fillstyle1 is None else self.fillstyle1.index
        lsi  = 0 if self.linestyle  is None else self.linestyle.index

        fbit = 0 if self.fillstyle0 is None else style_list_bits(self.fillstyle0.parent)
        lbit = 0 if self.linestyle  is None else style_list_bits(self.linestyle.parent)
        
        from pypy.translator.avm.tags import DefineShape
        
        new_styles = ((DefineShape._current_variant > 1) and
                     ((self.linestyles != None and len(self.linestyles) > 0) or
                      (self.fillstyles != None and len(self.fillstyles) > 0)))

        bits.write_bit(False)       # TypeFlag
        bits.write_bit(new_styles)  # StateNewStyles
        bits.write_bit(lsi  > 0)    # StateLineStyle
        bits.write_bit(fsi0 > 0)    # StateFillStyle0
        bits.write_bit(fsi1 > 0)    # StateFillStyle1

        move_flag = self.delta_x != 0 or self.delta_y != 0

        if move_flag:
            bits += XY(self.delta_x, self.delta_y).serialize()

        if fsi0 > 0:  bits.write_int_value(fsi0, fbit) # FillStyle0
        if fsi1 > 0:  bits.write_int_value(fsi1, fbit) # FillStyle1
        if lsi  > 0:  bits.write_int_value(lsi,  lbit) # LineStyle
        
        if new_styles:
            bits += ShapeWithStyle._serialize_style_list(self.fillstyles) # FillStyles
            bits += ShapeWithStyle._serialize_style_list(self.linestyles) # LineStyles

            bits.write_int_value(style_list_bits(self.fillstyles), 4) # FillBits
            bits.write_int_value(style_list_bits(self.linestyles), 4) # LineBits

        return bits
