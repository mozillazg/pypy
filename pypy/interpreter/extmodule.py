"""

Helpers to build extension modules.

"""

from pypy.interpreter.gateway import DictProxy
from pypy.interpreter.miscutils import InitializedClass
from pypy.interpreter.baseobjspace import Wrappable


class ExtModule(Wrappable):
    """An empty extension module.
    Non-empty extension modules are made by subclassing ExtModule."""

    def __init__(self, space):
        self.space = space
        self.w_dict = self._appdict.makedict(space, self)

    __metaclass__ = InitializedClass
    def __initclass__(cls):
        # make sure that the class has its own appdict
        if '_appdict' not in cls.__dict__:
            cls._appdict = DictProxy(implicitspace=True,
                                     implicitself=True)
        # automatically publish all functions from this class
        cls._appdict.exportall(cls.__dict__)
        # automatically import all app_ functions
        cls._appdict.importall(cls.__dict__, cls)

    def __getattr__(self, attr):
        # XXX temporary, for use by objspace.trivial and
        # objspace.std.cpythonobject
        try:
            return self.__class__._appdict.content[attr]
        except KeyError:
            raise AttributeError, attr
