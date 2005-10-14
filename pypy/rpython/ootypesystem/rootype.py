from pypy.annotation import model as annmodel
from pypy.rpython.rmodel import Repr

class __extend__(annmodel.SomeOOInstance):
    def rtyper_makerepr(self, rtyper):
        return OOInstanceRepr(self.ootype)
    def rtyper_makekey(self):
        return self.__class__, self.ootype

class OOInstanceRepr(Repr):
    def __init__(self, ootype):
        self.lowleveltype = ootype

class __extend__(annmodel.SomeOOClass):
    pass

class __extend__(annmodel.SomeOOBoundMeth):
    pass

class __extend__(annmodel.SomeOOStaticMeth):
    pass
