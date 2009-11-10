
from pypy.translator.avm.tags import ShapeWithStyle
from pypy.translator.avm.records import StyleChangeRecord, CurvedEdgeRecord, StraightEdgeRecord

class Circle(object):

    def __init__(self, x, y, radius, linestyle, fillstyle0, fillstyle1):
        self.x = x
        self.y = y
        self.radius = radius
        self.linestyle = linestyle
        self.fillstyle0 = fillstyle0
        self.fillstyle1 = fillstyle1

    def to_shape(self):
        shape = ShapeWithStyle()

        if self.linestyle: shape.add_line_style(self.linestyle)
        if self.fillstyle0: shape.add_fill_style(self.fillstyle0)
        if self.fillstyle1: shape.add_fill_style(self.fillstyle1)

        # Precalculated:
        # math.tan(math.radians(22.5)) = 0.41421356237309503
        # math.sin(math.radians(45))   = 0.70710678118654746
        
        c = self.radius * 0.41421356237309503
        a = self.radius * 0.70710678118654746 - c

        shape.add_shape_record(StyleChangeRecord(self.x + self.radius, self.y, self.linestyle, self.fillstyle0, self.fillstyle1))
        # 0 to PI/2
        shape.add_shape_record(CurvedEdgeRecord(0, -c, -a, -a))
        shape.add_shape_record(CurvedEdgeRecord(-a, -a, -c, 0))

        # PI/2 to PI
        shape.add_shape_record(CurvedEdgeRecord(-c, 0, -a, a))
        shape.add_shape_record(CurvedEdgeRecord(-a, a, 0, c))

        # PI to 3PI/2
        shape.add_shape_record(CurvedEdgeRecord(0, c, a, a))
        shape.add_shape_record(CurvedEdgeRecord(a, a, c, 0))

        # 3PI/2 to 2PI
        shape.add_shape_record(CurvedEdgeRecord(c, 0, a, -a))
        shape.add_shape_record(CurvedEdgeRecord(a, -a, 0, -c))

        return shape
