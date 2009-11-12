
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
     GetSetProperty, interp_attrproperty, descr_get_dict, descr_set_dict
from pypy.interpreter.gateway import interp2app

class W_BaseException(Wrappable):
    """Superclass representing the base of the exception hierarchy.

    The __getitem__ method is provided for backwards-compatibility
    and will be deprecated at some point. 
    """
    w_dict = None

    def __init__(self, space, args_w):
        self.args_w = args_w
        self.space = space
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

    def getdict(self):
        if self.w_dict is None:
            self.w_dict = self.space.newdict()
        return self.w_dict

    def setdict(self, space, w_dict):
        if not space.is_true(space.isinstance( w_dict, space.w_dict )):
            raise OperationError( space.w_TypeError, space.wrap("setting exceptions's dictionary to a non-dict") )
        self.w_dict = w_dict


def _new(cls):
    def descr_new_base_exception(space, w_subtype, args_w):
        exc = space.allocate_instance(cls, w_subtype)
        cls.__init__(exc, space, args_w)
        return space.wrap(exc)
    descr_new_base_exception.unwrap_spec = [ObjSpace, W_Root, 'args_w']
    descr_new_base_exception.func_name = 'descr_new_' + cls.__name__
    return interp2app(descr_new_base_exception)

W_BaseException.typedef = TypeDef(
    'BaseException',
    __doc__ = W_BaseException.__doc__,
    __new__ = _new(W_BaseException),
    __str__ = interp2app(W_BaseException.descr_str),
    __repr__ = interp2app(W_BaseException.descr_repr),
    __dict__ = GetSetProperty(descr_get_dict, descr_set_dict,
                              cls=W_BaseException),
    message = interp_attrproperty_w('w_message', W_BaseException),
    args = GetSetProperty(W_BaseException.descr_getargs),
)

def _new_exception(name, base, docstring, **kwargs):
    class W_Exception(base):
        __doc__ = docstring

    W_Exception.__name__ = 'W_' + name

    for k, v in kwargs.items():
        kwargs[k] = interp2app(v.__get__(None, W_Exception))
    W_Exception.typedef = TypeDef(
        name,
        base.typedef,
        __doc__ = W_Exception.__doc__,
        __new__ = _new(W_Exception),
        **kwargs
    )
    return W_Exception

W_Exception = _new_exception('Exception', W_BaseException,
                         """Common base class for all non-exit exceptions.""")

W_GeneratorExit = _new_exception('GeneratorExit', W_Exception,
                          """Request that a generator exit.""")

W_StandardError = _new_exception('StandardError', W_Exception,
                         """Base class for all standard Python exceptions.""")

W_ValueError = _new_exception('ValueError', W_StandardError,
                         """Inappropriate argument value (of correct type).""")

W_ImportError = _new_exception('ImportError', W_StandardError,
                  """Import can't find module, or can't find name in module.""")

W_RuntimeError = _new_exception('RuntimeError', W_StandardError,
                     """Unspecified run-time error.""")

W_UnicodeError = _new_exception('UnicodeError', W_ValueError,
                          """Unicode related error.""")


class W_UnicodeTranslateError(W_UnicodeError):
    """Unicode translation error."""
    def __init__(self, space, w_obj, w_start, w_end, w_reason):
        self.object = space.unicode_w(w_obj)
        self.start = space.int_w(w_start)
        self.end = space.int_w(w_end)
        self.reason = space.str_w(w_reason)
        W_BaseException.__init__(self, space, [w_obj, w_start, w_end, w_reason])

    def descr_str(self, space):
        return space.appexec([space.wrap(self)], """(self):
            if self.end == self.start + 1:
                badchar = ord(self.object[self.start])
                if badchar <= 0xff:
                    return "can't translate character u'\\\\x%02x' in position %d: %s" % (badchar, self.start, self.reason)
                if badchar <= 0xffff:
                    return "can't translate character u'\\\\u%04x' in position %d: %s"%(badchar, self.start, self.reason)
                return "can't translate character u'\\\\U%08x' in position %d: %s"%(badchar, self.start, self.reason)
            return "can't translate characters in position %d-%d: %s" % (self.start, self.end - 1, self.reason)
        """)
    descr_str.unwrap_spec = ['self', ObjSpace]

def descr_new_unicode_translate_error(space, w_subtype, w_obj, w_start, w_end,
                                      w_reason):
    exc = space.allocate_instance(W_UnicodeTranslateError, w_subtype)
    W_UnicodeTranslateError.__init__(exc, space, w_obj, w_start,
                                     w_end, w_reason)
    return space.wrap(exc)

def readwrite_attrproperty(name, cls, unwrapname):
    def fget(space, obj):
        return space.wrap(getattr(obj, name))
    def fset(space, obj, w_val):
        setattr(obj, name, getattr(space, unwrapname)(w_val))
    return GetSetProperty(fget, fset, cls=cls)

W_UnicodeTranslateError.typedef = TypeDef(
    'UnicodeTranslateError',
    W_UnicodeError.typedef,
    __doc__ = W_UnicodeTranslateError.__doc__,
    __new__ = interp2app(descr_new_unicode_translate_error),
    __str__ = interp2app(W_UnicodeTranslateError.descr_str),
    object = readwrite_attrproperty('object', W_UnicodeTranslateError, 'unicode_w'),
    start  = readwrite_attrproperty('start', W_UnicodeTranslateError, 'int_w'),
    end    = readwrite_attrproperty('end', W_UnicodeTranslateError, 'int_w'),
    reason = readwrite_attrproperty('reason', W_UnicodeTranslateError, 'str_w'),
)

W_LookupError = _new_exception('LookupError', W_StandardError,
                               """Base class for lookup errors.""")

def key_error_str(self, space):
    if len(self.args_w) == 0:
        return space.wrap('')
    elif len(self.args_w) == 1:
        return space.repr(self.args_w[0])
    else:
        return space.str(space.newtuple(self.args_w))
key_error_str.unwrap_spec = ['self', ObjSpace]
    
W_KeyError = _new_exception('KeyError', W_LookupError,
                            """Mapping key not found.""",
                            __str__ = key_error_str)
