
from pypy.rpython.extregistry import ExtRegistryEntry
from pypy.annotation import model as annmodel

class JudyTree(dict):
    pass

class SomeJudyTree(annmodel.SomeObject):
    def rtyper_makerepr(self, rtyper):
        from pypy.rpython.rjudy import JudyRepr
        return JudyRepr(rtyper)

    def method_free(self):
        return annmodel.s_None

class JudyTreeEntry(ExtRegistryEntry):
    """ This registers JudyTree to be special-treated by a translation
    toolchain
    """
    _about_ = JudyTree

    def compute_result_annotation(self):
        return SomeJudyTree()

    def specialize_call(self, hop):
        return hop.r_result.rtype_new(hop)
