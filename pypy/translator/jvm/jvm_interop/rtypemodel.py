import utils
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

    def rtype_getattr(self, hop):
        attrname = hop.args_v[1].value
        if attrname in self.jvm_class_wrapper._static_method_names:
            meth = ootype._static_meth(hop.r_result.lowleveltype)
            meth._callable = utils.call_method(getattr(self.jvm_class_wrapper, attrname), static=True)
            return hop.inputconst(hop.r_result.lowleveltype, meth)
        else:
            raise AssertionError("We don't support static fields yet!")
#            assert attrname in self.cli_class._static_fields
#            TYPE = self.cli_class._static_fields[attrname]
#            c_class = hop.inputarg(hop.args_r[0], arg=0)
#            c_name = hop.inputconst(ootype.Void, attrname)
#            return hop.genop("cli_getstaticfield", [c_class, c_name], resulttype=hop.r_result.lowleveltype)
