"""
Mutable Objects Factories.

A factory is associated to each point in the source that creates a mutable
object.  The factory remembers how general an object it has to create here.

"""

from pypy.annotation.pairtype import pair
from pypy.annotation.model import SomeImpossibleValue


class BlockedInference(Exception):
    """This exception signals the type inference engine that the situation
    is currently blocked, and that it should try to progress elsewhere."""

class NeedGeneralization(BlockedInference):
    """The mutable object s_mutable requires generalization.
    The *args are passed to the generalize() method of the factory."""

    def __init__(self, s_mutable, *args):
        BlockedInference.__init__(self, s_mutable, *args)
        for factory in s_mutable.factories:
            factory.generalize(*args)


#
#  Factories
#

class ListFactory:

    def __init__(self, block):
        self.block = block     # block containing the list creation op
        self.s_item = SomeImpossibleValue()

    def create(self):
        return SomeList(factories = {self: True}, s_item = self.s_item)

    def generalize(self, s_new_item):
        self.s_item = pair(self.s_item, s_new_item).union()
        self.block.invalidate()
