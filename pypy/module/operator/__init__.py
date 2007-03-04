from pypy.interpreter.mixedmodule import MixedModule 
from pypy.interpreter.error import OperationError 

class Module(MixedModule):
    """Operator Builtin Module. """

    appleveldefs = {} 
    
    names = ['__abs__', '__add__', '__and__',
             '__concat__', '__contains__', '__delitem__', '__delslice__',
             '__div__', '__doc__', '__eq__', '__floordiv__',
             '__ge__', '__getitem__', '__getslice__', '__gt__', '__inv__',
             '__invert__', '__le__', '__lshift__', '__lt__', '__mod__',
             '__mul__', '__name__', '__ne__', '__neg__', '__not__', '__or__',
             '__pos__', '__pow__', '__repeat__', '__rshift__', '__setitem__',
             '__setslice__', '__sub__', '__truediv__', '__xor__', 'abs', 'add',
             'and_', 'attrgetter', 'concat', 'contains', 'countOf', 'delitem',
             'delslice', 'div', 'division', 'eq', 'floordiv', 'ge', 'getitem',
             'getslice', 'gt', 'indexOf', 'inv', 'invert', 'isCallable',
             'isMappingType', 'isNumberType', 'isSequenceType', 'is_',
             'is_not', 'itemgetter', 'le', 'lshift', 'lt', 'mod', 'mul',
             'ne', 'neg', 'not_', 'or_', 'pos', 'pow', 'repeat', 'rshift',
             'sequenceIncludes', 'setitem', 'setslice', 'sub', 'truediv',
             'truth', 'xor']

    for name in names:
        appleveldefs[name] = 'app_operator.%s' % name
        
        
    interpleveldefs = {
        'index': 'interp_operator.index'
    }
