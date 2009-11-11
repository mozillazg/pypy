
"""Python's standard exception class hierarchy.

Before Python 1.5, the standard exceptions were all simple string objects.
In Python 1.5, the standard exceptions were converted to classes organized
into a relatively flat hierarchy.  String-based standard exceptions were
optional, or used as a fallback if some problem occurred while importing
the exception module.  With Python 1.6, optional string-based standard
exceptions were removed (along with the -X command line flag).

The class exceptions were implemented in such a way as to be almost
completely backward compatible.  Some tricky uses of IOError could
potentially have broken, but by Python 1.6, all of these should have
been fixed.  As of Python 1.6, the class-based standard exceptions are
now implemented in C, and are guaranteed to exist in the Python
interpreter.

Here is a rundown of the class hierarchy.  The classes found here are
inserted into both the exceptions module and the `built-in' module.  It is
recommended that user defined class based exceptions be derived from the
`Exception' class, although this is currently not enforced.

BaseException
 +-- SystemExit
 +-- KeyboardInterrupt
 +-- Exception
      +-- GeneratorExit
      +-- StopIteration
      +-- StandardError
      |    +-- ArithmeticError
      |    |    +-- FloatingPointError
      |    |    +-- OverflowError
      |    |    +-- ZeroDivisionError
      |    +-- AssertionError
      |    +-- AttributeError
      |    +-- EnvironmentError
      |    |    +-- IOError
      |    |    +-- OSError
      |    |         +-- WindowsError (Windows)
      |    |         +-- VMSError (VMS)
      |    +-- EOFError
      |    +-- ImportError
      |    +-- LookupError
      |    |    +-- IndexError
      |    |    +-- KeyError
      |    +-- MemoryError
      |    +-- NameError
      |    |    +-- UnboundLocalError
      |    +-- ReferenceError
      |    +-- RuntimeError
      |    |    +-- NotImplementedError
      |    +-- SyntaxError
      |    |    +-- IndentationError
      |    |         +-- TabError
      |    +-- SystemError
      |    +-- TypeError
      |    +-- ValueError
      |    |    +-- UnicodeError
      |    |         +-- UnicodeDecodeError
      |    |         +-- UnicodeEncodeError
      |    |         +-- UnicodeTranslateError
      +-- Warning
           +-- DeprecationWarning
           +-- PendingDeprecationWarning
           +-- RuntimeWarning
           +-- SyntaxWarning
           +-- UserWarning
           +-- FutureWarning
           +-- ImportWarning
           +-- UnicodeWarning
"""

from pypy.interpreter.baseobjspace import ObjSpace, Wrappable, W_Root
from pypy.interpreter.typedef import TypeDef, interp_attrproperty_w,\
     GetSetProperty
from pypy.interpreter.gateway import interp2app

class W_BaseException(Wrappable):
    """Superclass representing the base of the exception hierarchy.

    The __getitem__ method is provided for backwards-compatibility
    and will be deprecated at some point. 
    """

    def __init__(self, space, args_w):
        self.args_w = args_w
        if len(args_w) == 1:
            self.w_message = args_w[0]
        else:
            self.w_message = space.wrap("")

    def descr_str(self, space):
        lgt = len(self.args_w)
        if lgt == 0:
            return space.wrap('')
        elif lgt == 1:
            return space.str(self.w_message)
        else:
            return space.str(space.newtuple(self.args_w))
    descr_str.unwrap_spec = ['self', ObjSpace]

    def descr_repr(self, space):
        if self.args_w:
            args_repr = space.str_w(space.repr(space.newtuple(self.args_w)))
        else:
            args_repr = "()"
        clsname = self.getclass(space).getname(space, '?')
        return space.wrap(clsname + args_repr)
    descr_repr.unwrap_spec = ['self', ObjSpace]

    def descr_getargs(space, self):
        return space.newtuple(self.args_w)

def descr_new_base_exception(space, w_subtype, args_w):
    exc = space.allocate_instance(W_BaseException, w_subtype)
    W_BaseException.__init__(exc, space, args_w)
    return space.wrap(exc)
descr_new_base_exception.unwrap_spec = [ObjSpace, W_Root, 'args_w']

W_BaseException.typedef = TypeDef(
    'BaseException',
    __new__ = interp2app(descr_new_base_exception),
    __str__ = interp2app(W_BaseException.descr_str),
    __repr__ = interp2app(W_BaseException.descr_repr),
    message = interp_attrproperty_w('w_message', W_BaseException),
    args = GetSetProperty(W_BaseException.descr_getargs),
)
