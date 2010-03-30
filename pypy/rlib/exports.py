from pypy.rpython.lltypesystem.lltype import typeOf, ContainerType

EXPORTS_names = set()
EXPORTS_obj2name = {}

def export_struct(name, struct):
    assert name not in EXPORTS_names, "Duplicate export " + name
    assert isinstance(typeOf(struct), ContainerType)
    EXPORTS_names.add(name)
    EXPORTS_obj2name[struct] = name
