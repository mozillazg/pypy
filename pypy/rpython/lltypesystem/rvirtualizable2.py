from pypy.rpython.lltypesystem import llmemory
from pypy.rpython.lltypesystem.rclass import InstanceRepr
from pypy.rpython.rvirtualizable2 import AbstractVirtualizable2InstanceRepr


JITFRAMEPTR = llmemory.GCREF


class Virtualizable2InstanceRepr(AbstractVirtualizable2InstanceRepr, InstanceRepr):

    def _setup_repr_llfields(self):
        llfields = []
        if self.top_of_virtualizable_hierarchy:
            llfields.append(('jit_frame', JITFRAMEPTR))
        return llfields
