"""
Weakref support in RPython.  Supports ref() without callbacks,
and a limited version of WeakValueDictionary.  LLType only for now!
"""

import weakref
from weakref import ref


class RWeakValueDictionary(object):
    """A limited dictionary containing weak values.
    Only supports string keys.
    """

    def __init__(self, valueclass):
        self._dict = weakref.WeakValueDictionary()
        self._valueclass = valueclass

    def get(self, key):
        return self._dict.get(key, None)

    def set(self, key, value):
        if value is None:
            self._dict.pop(key, None)
        else:
            assert isinstance(value, self._valueclass)
            self._dict[key] = value


# ____________________________________________________________

from pypy.rpython import controllerentry

@staticmethod
def _get_controller():
    from pypy.rlib.rweakrefimpl import WeakDictController
    return WeakDictController()

class Entry(controllerentry.ControllerEntry):
    _about_ = RWeakValueDictionary
    _controller_ = _get_controller

class Entry(controllerentry.ControllerEntryForPrebuilt):
    _type_ = RWeakValueDictionary
    _controller_ = _get_controller
