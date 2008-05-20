from pypy.lang.smalltalk import classtable
from pypy.lang.smalltalk import constants
from pypy.lang.smalltalk import model

# ___________________________________________________________________________
# Global Data


def wrap_char_table():
    global w_charactertable
    def bld_char(i):
        w_cinst = classtable.w_Character.as_class_get_shadow().new()
        w_cinst.store(constants.CHARACTER_VALUE_INDEX,
                      model.W_SmallInteger(i))
        return w_cinst
    w_charactertable = model.W_PointersObject(classtable.classtable['w_Array'], 256)
    for i in range(256):
        w_charactertable.atput0(i, bld_char(i))

wrap_char_table()


# Very special nil hack: in order to allow W_PointersObject's to
# initialize their fields to nil, we have to create it in the model
# package, and then patch up its fields here:
w_nil = model.w_nil
w_nil.w_class = classtable.classtable['w_UndefinedObject']

w_true  = classtable.classtable['w_True'].as_class_get_shadow().new()
w_false = classtable.classtable['w_False'].as_class_get_shadow().new()
w_minus_one = model.W_SmallInteger(-1)
w_zero = model.W_SmallInteger(0)
w_one = model.W_SmallInteger(1)
w_two = model.W_SmallInteger(2)

# We use indirection because translated globals are assumed to be constant
class ObjectTableHolder(object):
    pass

object_table_holder = ObjectTableHolder()
object_table_holder.objtable = {}

def get_objtable():
    return object_table_holder.objtable

for name in constants.objects_in_special_object_table:
    name = "w_" + name
    try:
        get_objtable()[name] = globals()[name]
    except KeyError, e:
        get_objtable()[name] = None
