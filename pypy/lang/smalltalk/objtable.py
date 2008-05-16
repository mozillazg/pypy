from pypy.lang.smalltalk import classtable
from pypy.lang.smalltalk import constants
from pypy.lang.smalltalk import model

# ___________________________________________________________________________
# Global Data

def wrap_char_table():
    global w_charactertable
    def bld_char(i):
        w_cinst = classtable.w_Character.as_class_get_shadow().new(store=False)
        w_cinst.store(constants.CHARACTER_VALUE_INDEX,
                      model.W_SmallInteger(i))
        return w_cinst
    w_charactertable = model.W_PointersObject(classtable.classtable['w_Array'], 256)
    for i in range(256):
        w_charactertable.atput0(i, bld_char(i))

wrap_char_table()

w_true  = classtable.classtable['w_True'].as_class_get_shadow().new(store=False)
w_false = classtable.classtable['w_False'].as_class_get_shadow().new(store=False)
w_minus_one = model.W_SmallInteger(-1)
w_zero = model.W_SmallInteger(0)
w_one = model.W_SmallInteger(1)
w_two = model.W_SmallInteger(2)

# Very special nil hack: in order to allow W_PointersObject's to
# initialize their fields to nil, we have to create it in the model
# package, and then patch up its fields here:
w_nil = model.w_nil
w_nil.w_class = classtable.classtable['w_UndefinedObject']

objtable = {}
# XXX Used for non-PyPy way of doing become.
objects = []

for name in constants.objects_in_special_object_table:
    name = "w_" + name
    try:
        objtable[name] = globals()[name]
    except KeyError, e:
        objtable[name] = None
