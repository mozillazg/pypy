"""
Mutable Objects Factories.

A factory is associated to each point in the source that creates a mutable
object.  The factory remembers how general an object it has to create here.

"""

from pypy.annotation.pairtype import pair
from pypy.annotation.model import SomeImpossibleValue, SomeList


class BlockedInference(Exception):
    """This exception signals the type inference engine that the situation
    is currently blocked, and that it should try to progress elsewhere."""
    invalidatefactories = ()  # factories that need to be invalidated

class NeedGeneralization(BlockedInference):
    """The mutable object s_mutable requires generalization.
    The *args are passed to the generalize() method of the factory."""

    def __init__(self, s_mutable, *args):
        BlockedInference.__init__(self, s_mutable, *args)
        for factory in s_mutable.factories:
            factory.generalize(*args)
        self.invalidatefactories = s_mutable.factories


#
#  Factories
#

class ListFactory:
    s_item = SomeImpossibleValue()

    def create(self):
        return SomeList(factories = {self: True}, s_item = self.s_item)

    def generalize(self, s_new_item):
        self.s_item = pair(self.s_item, s_new_item).union()
