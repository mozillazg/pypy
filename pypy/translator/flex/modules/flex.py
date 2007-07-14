from pypy.rpython.extfunc import genericcallable, register_external
from pypy.rpython.ootypesystem.bltregistry import BasicExternal, MethodDesc


class Button( BasicExternal ):
    
    _fields = {
        'label' : str,
        '_x' : int,
        '_y' : int,
    }
    _render_class = 'Button'

def addChild(e):
    pass

register_external(addChild, args=[Button])
#addChild._annspecialcase_ = 'specialize:argtype(0)'

