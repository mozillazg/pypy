from pypy.rpython.extregistry import ExtRegistryEntry
from pypy.rlib.objectmodel import CDefinedIntSymbolic

def purefunction(func):
    func._pure_function_ = True
    return func

def hint(x, **kwds):
    return x

class Entry(ExtRegistryEntry):
    _about_ = hint

    def compute_result_annotation(self, s_x, **kwds_s):
        from pypy.annotation import model as annmodel
        s_x = annmodel.not_const(s_x)
        if 's_access_directly' in kwds_s:
            if isinstance(s_x, annmodel.SomeInstance):
                from pypy.objspace.flow.model import Constant
                classdesc = s_x.classdef.classdesc
                virtualizable = classdesc.read_attribute('_virtualizable_',
                                                         Constant(False)).value
                if virtualizable:
                    flags = s_x.flags.copy()
                    flags['access_directly'] = True
                    s_x = annmodel.SomeInstance(s_x.classdef,
                                                s_x.can_be_None,
                                                flags)
        return s_x

    def specialize_call(self, hop, **kwds_i):
        from pypy.rpython.lltypesystem import lltype
        hints = {}
        for key, index in kwds_i.items():
            s_value = hop.args_s[index]
            if not s_value.is_constant():
                from pypy.rpython.error import TyperError
                raise TyperError("hint %r is not constant" % (key,))
            assert key.startswith('i_')
            hints[key[2:]] = s_value.const
        v = hop.inputarg(hop.args_r[0], arg=0)
        c_hint = hop.inputconst(lltype.Void, hints)
        hop.exception_cannot_occur()
        return hop.genop('hint', [v, c_hint], resulttype=v.concretetype)


def we_are_jitted():
    return False
# timeshifts to True

_we_are_jitted = CDefinedIntSymbolic('0 /* we are not jitted here */',
                                     default=0)

class Entry(ExtRegistryEntry):
    _about_ = we_are_jitted

    def compute_result_annotation(self):
        from pypy.annotation import model as annmodel
        return annmodel.SomeInteger(nonneg=True)

    def specialize_call(self, hop):
        from pypy.rpython.lltypesystem import lltype
        return hop.inputconst(lltype.Signed, _we_are_jitted)

def _is_early_constant(x):
    return False

class Entry(ExtRegistryEntry):
    _about_ = _is_early_constant

    def compute_result_annotation(self, s_value):
        from pypy.annotation import model as annmodel
        s = annmodel.SomeBool()
        if s_value.is_constant():
            s.const = True
        return s

    def specialize_call(self, hop):
        from pypy.rpython.lltypesystem import lltype
        if hop.s_result.is_constant():
            assert hop.s_result.const
            return hop.inputconst(lltype.Bool, True)
        v, = hop.inputargs(hop.args_r[0])
        return hop.genop('is_early_constant', [v], resulttype=lltype.Bool)


def jit_merge_point(green=(), red=()):
    pass

def can_enter_jit(green=(), red=()):
    pass

class Entry(ExtRegistryEntry):
    _about_ = jit_merge_point, can_enter_jit

    def compute_result_annotation(self, s_green=None, s_red=None):
        from pypy.annotation import model as annmodel
        assert s_green is None or isinstance(s_green, annmodel.SomeTuple)
        assert s_red is None or isinstance(s_red, annmodel.SomeTuple)
        return annmodel.s_None

    def specialize_call(self, hop, **kwds_i):
        from pypy.rpython.error import TyperError
        from pypy.rpython.lltypesystem import lltype
        lst = kwds_i.values()
        lst.sort()
        if lst != range(hop.nb_args):
            raise TyperError("%s() takes only keyword arguments" % (
                self.instance.__name__,))
        greens_v = []
        reds_v = []
        if 'i_green' in kwds_i:
            i = kwds_i['i_green']
            r_green_tuple = hop.args_r[i]
            v_green_tuple = hop.inputarg(r_green_tuple, arg=i)
            for j in range(len(r_green_tuple.items_r)):
                v = r_green_tuple.getitem(hop.llops, v_green_tuple, j)
                greens_v.append(v)
        if 'i_red' in kwds_i:
            i = kwds_i['i_red']
            r_red_tuple = hop.args_r[i]
            v_red_tuple = hop.inputarg(r_red_tuple, arg=i)
            for j in range(len(r_red_tuple.items_r)):
                v = r_red_tuple.getitem(hop.llops, v_red_tuple, j)
                reds_v.append(v)

        hop.exception_cannot_occur()
        vlist = [hop.inputconst(lltype.Signed, len(greens_v)),
                 hop.inputconst(lltype.Signed, len(reds_v))]
        vlist.extend(greens_v)
        vlist.extend(reds_v)
        return hop.genop(self.instance.__name__, vlist,
                         resulttype=lltype.Void)
