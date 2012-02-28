from pypy.rpython.ootypesystem import ootype
from pypy.rpython.rmodel import Repr

class JvmClassWrapperRepr(Repr):
    lowleveltype = ootype.Void

    def __init__(self, jvm_class_wrapper):
        self.jvm_class_wrapper = jvm_class_wrapper

    def rtype_simple_call(self, hop):
        jvm_native_instance = hop.r_result.lowleveltype
        args = [hop.inputarg(r_arg, i) for (i, r_arg) in enumerate(hop.args_r[1:], start=1)]
        class_and_args = [hop.inputconst(ootype.Void, jvm_native_instance)] + args
        return hop.genop("new", class_and_args, resulttype=jvm_native_instance)
