from pypy.interpreter.mixedmodule import MixedModule 
from pypy.interpreter.error import OperationError 

class Module(MixedModule):
    """Operator Builtin Module. """

    appleveldefs = {} 
    
    app_names = ['__delslice__', '__doc__','__getslice__', '__name__',
             '__repeat__', '__setslice__', '__truediv__','attrgetter',
             'concat', 'contains', 'countOf', 'delitem',
             'delslice', 'division', 'getslice', 'indexOf',
             'isCallable','isMappingType', 'isNumberType', 'isSequenceType',
             'itemgetter','repeat', 'sequenceIncludes', 'setslice',
             'truediv']

    for name in app_names:
        appleveldefs[name] = 'app_operator.%s' % name

    interp_names = ['index', '__abs__', '__add__', '__and__',
                    '__concat__', '__contains__', '__delitem__','__div__',
                    '__eq__', '__floordiv__', '__ge__', '__getitem__',
                    '__gt__', '__inv__', '__invert__', '__le__',
                    '__lshift__', '__lt__', '__mod__', '__mul__',
                    '__ne__', '__neg__', '__not__', '__or__',
                    '__pos__', '__pow__', '__rshift__', '__setitem__',
                    '__sub__', '__xor__', 'abs', 'add',
                    'and_', 'div', 'eq', 'floordiv',
                    'ge', 'getitem', 'gt', 'inv',
                    'invert', 'is_', 'is_not', 'le',
                    'lshift', 'lt', 'mod', 'mul',
                    'ne', 'neg', 'not_', 'or_',
                    'pos', 'pow', 'rshift', 'setitem',
                    'sub', 'truth', 'xor']
    interpleveldefs = {}

    for name in interp_names:
        interpleveldefs[name] = 'interp_operator.%s' % name
