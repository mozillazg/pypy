
""" String builder interface
"""

from pypy.rpython.extregistry import ExtRegistryEntry
from pypy.rpython.annlowlevel import llhelper

INIT_SIZE = 100 # XXX tweak

class StringBuilder(object):
    def __init__(self, init_size=INIT_SIZE):
        self.l = []

    def append(self, s):
        self.l.append(s)

    def build(self):
        return "".join(self.l)

class StringBuilderEntry(ExtRegistryEntry):
    _about_ = StringBuilder

    def compute_result_annotation(self, s_init_size=None):
        from pypy.rpython.rbuilder import SomeStringBuilder
        if s_init_size is not None:
            assert s_init_size.is_constant()
            init_size = s_init_size.const
        else:
            init_size = INIT_SIZE
        return SomeStringBuilder(init_size)

    def specialize_call(self, hop):
        return hop.r_result.rtyper_new(hop)
