
from pypy.rpython.rbuilder import AbstractStringBuilderRepr
from pypy.rpython.ootypesystem import ootype

class StringBuilderRepr(AbstractStringBuilderRepr):
    lowleveltype = ootype.StringBuilder

    @staticmethod
    def ll_new(init_size):
        return ootype.new(ootype.StringBuilder)

    @staticmethod
    def ll_append_char(builder, char):
        builder.ll_append_char(char)

    @staticmethod
    def ll_append(builder, string):
        builder.ll_append(string)

    @staticmethod
    def ll_build(builder):
        return builder.ll_build()

stringbuilder_repr = StringBuilderRepr()
