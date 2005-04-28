"""
Implementation of the interpreter-level functions in the module unicodedata.
"""
from pypy.interpreter.gateway import NoneNotWrapped
from pypy.module.unicodedata import unicodedb
from pypy.interpreter.error import OperationError

def unichr_to_code_w(space, w_unichr):
    if not space.is_true(space.isinstance(w_unichr, space.w_unicode)):
        raise TypeError, 'argument 1 must be unicode'
    if not space.int_w(space.len(w_unichr)) == 1:
        raise TypeError, 'need a single Unicode character as parameter'
    return space.int_w(space.ord(w_unichr))

def lookup(space, w_name):
    name = space.str_w(w_name)
    try:
        code = unicodedb.charcodeByName[name]
    except KeyError:
        msg = space.mod(space.wrap("undefined character name '%s'"), w_name)
        raise OperationError(space.w_KeyError, msg)
    return space.call_function(space.getattr(space.w_builtin, 'unichr'),
                               space.wrap(code))

def name(space, w_unichr, w_default=NoneNotWrapped):
    code = unichr_to_code_w(space, w_unichr)
    try:
        name = unicodedb.charnameByCode[code]
    except KeyError:
        if w_default is not None:
            return w_default
        raise OperationError(space.w_ValueError, space.wrap('no such name'))
    return space.wrap(name)


def decimal(space, w_unichr, default=NoneNotWrapped):
    code = unichr_to_code_w(space, w_unichr)
    try:
        return space.wrap(unicodedb.decimalValue[code])
    except KeyError:
        pass
    if w_default is not None:
        return w_default
    raise OperationError(space.w_ValueError, space.wrap('not a decimal'))

def digit(space, w_unichr, w_default=NoneNotWrapped):
    code = unichr_to_code_w(space, w_unichr)
    try:
        return space.wrap(unicodedb.digitValue[code])
    except KeyError:
        pass
    if w_default is not None:
        return w_default
    raise OperationError(space.w_ValueError, space.wrap('not a digit'))

def numeric(space, w_unichr, w_default=NoneNotWrapped):
    code = unichr_to_code_w(space, w_unichr)
    try:
        return space.wrap(unicodedb.numericValue[code])
    except KeyError:
        pass
    if w_default is not None:
        return w_default
    raise OperationError(space.w_ValueError,
                         space.wrap('not a numeric character'))

def category(space, w_unichr):
    code = unichr_to_code_w(space, w_unichr)
    return space.wrap(unicodedb.category.get(code, 'Cn'))

def bidirectional(space, w_unichr):
    code = unichr_to_code_w(space, w_unichr)
    return space.wrap(unicodedb.bidirectional.get(code, ''))

def combining(space, w_unichr):
    code = unichr_to_code_w(space, w_unichr)
    return space.wrap(unicodedb.combining(code, 0)

def mirrored(space, w_unichr):
    code = unichr_to_code_w(space, w_unichr)
    return space.wrap(unicodedb.mirrored(code, 0)


def decomposition(space, w_unichr):
    code = unichr_to_code_w(space, w_unichr)
    return space.wrap('')

def normalize(space, w_form, w_unistr):
    form = space.str_w(w_form)
    if not space.is_true(space.isinstance(w_unistr, space.w_unicode)):
        raise TypeError, 'argument 2 must be unicode'
    if form == 'NFC':
        return w_unistr
    if form == 'NFD':
        return w_unistr
    if form == 'NFKC':
        return w_unistr
    if form == 'NFKD':
        return w_unistr
    raise OperationError(space.w_ValueError,
                         space.wrap('invalid normalization form'))
