from pypy.rpython.error import TyperError
from pypy.rpython.ootypesystem.rootype import OOInstanceRepr
from pypy.rpython.rlist import ll_len_foldable
from pypy.tool.pairtype import pairtype
import utils
from pypy.translator.jvm.jvm_interop.annmodel import SomeJvmNativeStaticMeth
from pypy.rpython.ootypesystem import ootype
from pypy.rpython.rmodel import Repr, IntegerRepr, inputconst


class JvmClassWrapperRepr(Repr):
    lowleveltype = ootype.Void

    def __init__(self, jvm_class_wrapper):
        self.jvm_class_wrapper = jvm_class_wrapper

    def rtype_simple_call(self, hop):
        jvm_native_instance = hop.r_result.lowleveltype
        args = [hop.inputarg(r_arg, i) for (i, r_arg) in enumerate(hop.args_r[1:], start=1)]
        class_and_args = [hop.inputconst(ootype.Void, jvm_native_instance)] + args
        hop.exception_is_here()
        return hop.genop('new', class_and_args, resulttype=jvm_native_instance)

    def rtype_getattr(self, hop):
        attrname = hop.args_v[1].value
        if isinstance(hop.s_result, SomeJvmNativeStaticMeth):
            assert attrname in self.jvm_class_wrapper._static_method_names
            # methods are not values in java, so just return nothing. Information about
            # the static method being called is already present in the 'simple_call' op
            # that follows this hop.
            return hop.inputconst(ootype.Void, None)
        else:
            assert attrname in self.jvm_class_wrapper._static_field_names or attrname == 'class_'
            c_class = hop.inputarg(hop.args_r[0], arg=0)
            c_name = hop.inputconst(ootype.Void, attrname)
            hop.exception_cannot_occur()
            return hop.genop('oogetstaticfield', [c_class, c_name], resulttype=hop.r_result.lowleveltype)


class JvmNativeStaticMethRepr(Repr):
    # Methods are not first class values on the JVM:
    lowleveltype = ootype.Void

    def __init__(self, METHODTYPE, name, rjvm_class_wrapper):
        self.method_type = METHODTYPE
        self.name = name
        self.rjvm_class_wrapper = rjvm_class_wrapper

    def rtype_simple_call(self, hop):
        if isinstance(self.method_type, ootype._overloaded_meth):
            method_type = ootype.typeOf(self.method_type._resolver.resolve(hop.args_r[1:]))
        else:
            method_type = self.method_type

        full_name = self.rjvm_class_wrapper.__name__ + '.' + self.name
        rjvm_method_wrapper = getattr(self.rjvm_class_wrapper, self.name)
        method = ootype.static_meth(method_type, full_name)
        call_rjvm_method = utils.call_method(rjvm_method_wrapper, method, static=True)
        method._callable = call_rjvm_method
        method.is_native = True
        method_const = hop.inputconst(method_type, method)

        vlist = hop.inputargs(*hop.args_r)[1:]
        hop.exception_is_here()
        return hop.genop('direct_call', [method_const] + vlist, resulttype=method_type.RESULT)


class __extend__(pairtype(OOInstanceRepr, IntegerRepr)):

    def rtype_getitem((r_inst, r_int), hop):
        if not isinstance(r_inst.lowleveltype, ootype.Array):
            raise TyperError("getitem() on a non-array instance")
        c_getitem = inputconst(ootype.Void, "ll_getitem_fast")
        vlist = hop.inputargs(*hop.args_r)
        hop.exception_is_here()
        return hop.genop('oosend', [c_getitem] + vlist, resulttype=hop.r_result)

    def rtype_setitem((r_inst, r_int), hop):
        if not isinstance(r_inst.lowleveltype, ootype.Array):
            raise TyperError("setitem() on a non-array instance")
        c_setitem = inputconst(ootype.Void, "ll_setitem_fast")
        vlist = hop.inputargs(*hop.args_r)
        hop.exception_is_here()
        # In ootype, arrays have methods. The ll_setitem_fast method is used
        # to store values in arrays. This method call gets translated to
        # *astore jvm opcodes by the code generator.
        return hop.genop('oosend', [c_setitem] + vlist, resulttype=ootype.Void)

class __extend__(OOInstanceRepr):

    def rtype_len(self, hop):
        if not isinstance(self.lowleveltype, ootype.Array):
            raise TypeError("len() on a non-array instance")
        vlist = hop.inputargs(self)
        hop.exception_cannot_occur()
        return hop.gendirectcall(ll_len_foldable, *vlist)
