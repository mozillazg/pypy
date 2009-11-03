
from pypy.translator.avm.swf import SwfData
from pypy.translator.avm.tags import SetBackgroundColor, DefineShape, End
from pypy.translator.avm.records import ShapeWithStyle, LineStyle, StraightEdgeRecord, StyleChangeRecord

linestyle = LineStyle(3, 0x000000)

shape = ShapeWithStyle()
shape.add_line_style(linestyle)
shape.add_shape_record(StyleChangeRecord(20, 20, linestyle))
shape.add_shape_record(StraightEdgeRecord(100, 100))

swf = SwfData(400, 300)
swf.add_tag(SetBackgroundColor(0x333333))
swf.add_tag(DefineShape(shape))
swf.add_tag(End())
print swf.serialize()
