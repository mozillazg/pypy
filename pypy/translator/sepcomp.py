import os
import sys
import random
import pickle
import types

import pypy
from pypy.rlib.objectmodel import we_are_translated
from pypy.rlib.libffi import dlsym, dlopen, RTLD_GLOBAL, RTLD_NOW
from pypy.translator.tool.cbuild import ExternalCompilationInfo
from pypy.rpython.lltypesystem import rffi
from pypy.rpython.lltypesystem.rffi import llexternal, CConstant, VOIDP
from pypy.rlib.objectmodel import Symbolic
from pypy.rpython.lltypesystem import lltype
from pypy.annotation.model import lltype_to_annotation, SomeString, SomeInstance, SomeObject, SomePBC
from pypy.rpython.annlowlevel import llhelper, PseudoHighLevelCallable, PseudoHighLevelCallableEntry, MixLevelHelperAnnotator
from pypy.rpython.typesystem import getfunctionptr
from pypy.annotation.signature import annotationoftype
from pypy.rpython.lltypesystem.lltype import LowLevelType
from pypy.annotation import model as annmodel
from pypy.annotation.bookkeeper import getbookkeeper
from pypy.objspace.flow.model import Constant
from pypy.translator.simplify import get_functype
from pypy.tool.sourcetools import compile_template



class NonInheritable(type):
    def __init__(self, clsname, bases, namespace):
        for cls in bases:
            if isinstance(cls, NonInheritable):
                raise TypeError("While creating the class " + clsname + ": " + str(cls) +
                                " is not suitable as a base class")
        super(NonInheritable, self).__init__(clsname, bases, namespace)


class ExportTablePickler(pickle.Pickler):
    def persistent_id(self, obj):
        if obj is type(None): # grrrr
            return "NONETYPE"
        return None

class ExportTableUnpickler(pickle.Unpickler):
    def persistent_load(self, key):
        if key == "NONETYPE":
            return type(None)
        raise pickle.UnpicklingError, 'Invalid persistent id'



class ExternalClassRegistryImpl(object):
    classes_by_ci = {}
    def get_class(self, classinfo):
        try:
            cls = self.classes_by_ci[classinfo.key()]
        except KeyError:
            self.classes_by_ci[classinfo.key()] = cls = classinfo._build_class()
        return cls

external_class_registry = ExternalClassRegistryImpl()


class ClassInfo(object):
    def __init__(self, baseinfo, cls, inst, vtablename):
        self.cls = cls
        self.inst = inst
        self.vtablename = vtablename
        self.baseinfo = baseinfo

    def key(self):
        return self.vtablename

    def __repr__(self):
        return "<ClassInfo name=%r cls=%r inst=%r>" % (self.vtablename, self.cls, self.inst)

    def convert_llvalues(self, c_db):
        for name in ("cls", "inst"):
            new = []
            for key, attrname, val in getattr(self, name):
                if attrname is None:
                    if isinstance(val, lltype._ptr):
                        llvalue = val._obj
                        assert isinstance(llvalue, lltype._container)
                        assert hasattr(llvalue, "_exported")
                        llvalue._exported = True
                        handle = c_db.get(val)
                        T = lltype.Ptr(lltype.OpaqueType(handle, hints=dict(external_void=True)))
                        val = CConstant("&" + handle, T)
                    elif not "Signed" in repr(val): # XXX
                        import pdb; pdb.set_trace()

                new.append((key, attrname, val))
            setattr(self, name, new)

    def _build_class(self):
        if self.baseinfo is None:
            base = object
        else:
            base = external_class_registry.get_class(self.baseinfo)
        clsdict = dict(__slots__=(), _settled_=True, _force_virtual_=True, _importinfo_=self)
        for key, attrname, typ in self.cls:
            if attrname is None: # anonymous
                continue
            assert isinstance(typ, FunctionInfo) # XXX lift
            extfunc = typ.get_func()
            args_string = ", ".join(['arg_%i' % i for i in xrange(len(typ.s_args))])
            # XXX we dont have more of the sig than just the param count
            wrap = compile_template("""def wrap_func(%s): return extfunc(%s)""" % (args_string, args_string), "wrap_func")
            wrap.is_wrapping = extfunc
            sig_helpers = []
            def make_helper(i):
                def inputtypecalc(*arg):
                    extfunc.compute_rebuilt_args_result(getbookkeeper())
                    return extfunc.args_s_rebuilt[i]
                return inputtypecalc
            for i in xrange(len(typ.s_args)):
                sig_helpers.append(make_helper(i))
            wrap._annenforceargs_ = tuple(sig_helpers)
            wrap._force_virtual_ = True
            clsdict[attrname] = wrap
        newcls = type(str(self.vtablename), (base,), clsdict)
        return newcls


class Instance(object):
    def __init__(self, classinfo):
        self.classinfo = classinfo
    def __repr__(self):
        return "<Instance of %r>" % (self.classinfo, )


class FunctionInfo(object):
    def __init__(self, s_args, s_result, T_args, T_result):
        self.T_args = T_args
        self.T_result = T_result
        self.s_args = s_args
        self.s_result = s_result
        self.link_key = None

    def __repr__(self):
        return "<FunctionInfo, %r -> %r, %r -> %r>" % (self.T_args, self.T_result, self.s_args, self.s_result)

    def get_func(self, dll=False):
        smfc = SeparateModuleFunctionCallable(self.link_key, self.T_args, self.T_result, self.s_args, self.s_result, dll)
        return smfc


class ExportTable(object):
    """ A table with information about the exported symbols of a module compiled by pypy."""
    def __init__(self):
        self.functions = None
        self.classinfos_by_name = {}

        self.methods = set()
        self.functions_by_obj = {}
        self.classinfos_by_cdef = {}
        self.classes_by_ci = {}
        self.vtable_vals = {}
        self.fi_llvalues = {}

    def __repr__(self):
        return "<ExportTable funcs=%r classes=%r,%r>" % (self.functions, self.classinfos_by_cdef, self.classinfos_by_name)

    def convert_llvalues(self, c_database):
        for fi in self.functions_by_obj.values():
            dbname = c_database.get(self.fi_llvalues[fi])
            fi.link_key = dbname
        for cdef, ci in self.classinfos_by_cdef.items():
            dbname = c_database.getcontainernode(self.vtable_vals[ci]._obj).name
            ci.vtablename = (cdef.classdesc.pyobj._component_.name, cdef.name)
            ci.convert_llvalues(c_database)

    def load_entrypoint_annotations(self, translator, entrypoints):
        ann = translator.annotator
        for func, types in entrypoints:
            func = unwrap_meth_wrapper(func)
            graph = ann.bookkeeper.getdesc(func).getuniquegraph()
            inputargs = graph.getargs()
            s_list = []
            for var in inputargs:
                s_ann = ann.binding(var)
                s_ann_exp = s_ann.make_acceptable_in_interface()
                if s_ann_exp is None:
                    raise Exception("Unsuitable parameter type found: %r" % (s_ann, ))
                if s_ann_exp != s_ann:
                    ann.setbinding(var, s_ann_exp)
                s_list.append(s_ann_exp)
            s_ret = ann.binding(graph.getreturnvar())
            s_ret_exp = s_ret.make_acceptable_in_interface()
            if "str" in repr(s_ret): 1/0
            checktype = func._check_ret_type_
            if checktype is not None:
                if not isinstance(checktype, annmodel.SomeObject):
                    checktype = annotationoftype(checktype, ann.bookkeeper)
                checktype = checktype.make_acceptable_in_interface()
                if s_ret != annmodel.s_ImpossibleValue:
                    assert checktype == s_ret_exp, "Wrong type!"

            if s_ret != annmodel.s_ImpossibleValue:
                if s_ret_exp is None:
                    raise Exception("Unsuitable return type found: %r" % (s_ret,))
                if s_ret_exp is not s_ret:
                    ann.setbinding(graph.getreturnvar(), s_ret_exp)
            else:
                ann.setbinding(graph.getreturnvar(), checktype)
                s_ret_exp = checktype
            if "classdef=object" in repr(s_ret_exp): 1/0
            self.functions_by_obj[func] = FunctionInfo(s_list, s_ret_exp, None, None)

    def load_entrypoints(self, translator, entrypoints):
        rtyper = translator.rtyper
        from pypy.rpython.typesystem import getfunctionptr
        for func, types in entrypoints:
            func = unwrap_meth_wrapper(func)
            finfo = self.functions_by_obj[func]
            graph = translator.annotator.bookkeeper.getdesc(func).getuniquegraph()
            llvalue = getfunctionptr(graph)
            FT = llvalue._T
            new_args = []
            for i, arg in enumerate(FT.ARGS):
                new_args.append(self.opaquify_type(rtyper, arg, finfo.s_args[i]))
            ARGS = tuple(new_args)
            RESULT = self.opaquify_type(rtyper, FT.RESULT, finfo.s_result)

            finfo.T_args = ARGS
            finfo.T_result = RESULT
            self.fi_llvalues[finfo] = llvalue
            finfo.s_args = [self.externalize_annotation(s_arg) for s_arg in finfo.s_args]
            finfo.s_result = self.externalize_annotation(finfo.s_result)
        # even if clsdefs dont show up in the external interface of a function,
        # they might be exported and need to be available
        for clsdef in translator.annotator.getuserclassdefinitions():
            if clsdef.is_exported(False):
                self.get_classinfo(clsdef)


    def lookup_function(self, funcname):
        return self.functions[funcname]

    def lookup_class(self, classname):
        return self.classinfos_by_name[classname]

    def __getstate__(self):
        if self.functions is not None:
            return self.__dict__.copy()
        self.functions = {}
        for func, fi in self.functions_by_obj.items():
            if func in self.methods: # are linked via classinfo
                continue
            name = get_function_name(func)
            assert name not in self.functions
            self.functions[name] = fi
        odict = self.__dict__.copy()
        del odict['classinfos_by_cdef']
        del odict['classes_by_ci']
        del odict['functions_by_obj']
        del odict['methods']
        del odict['vtable_vals']
        del odict['fi_llvalues']
        return odict

    def __setstate__(self, d):
        self.__dict__.update(d)
        self.classes_by_ci = {}
        self.classinfos_by_cdef = None
        self.functions_by_obj = None

    def convertexportinfo_to_finfo(self, ei_items):
        result = []
        for key, name, typ in ei_items:
            if is_exported(typ):
                self.methods.add(typ)
                typ = self.functions_by_obj[typ]
            result.append((key, name, typ))
        return result

    def get_classinfo(self, cdef):
        try:
            return self.classinfos_by_cdef[cdef]
        except KeyError:
            if cdef is None:
                return None
            cdict = cdef.classdesc.classdict
            assert '_exported_' in cdict, "Found non-exported class type in interface: %r" % (cdef, )
            obj = cdef.classdesc.pyobj
            name = get_class_name(obj)
            ci = ClassInfo(self.get_classinfo(cdef.basedef), self.convertexportinfo_to_finfo(cdef.exportinfo_cls), self.convertexportinfo_to_finfo(cdef.exportinfo_inst), None)
            self.vtable_vals[ci] = cdef.exportinfo_vtableval
            cdef.exportinfo_vtableval._obj._exported = True
            self.classinfos_by_cdef[cdef] = ci
            assert name not in self.classinfos_by_name
            self.classinfos_by_name[name] = ci
            return ci

    def opaquify_type(self, rtyper, T, s_ann):
        if type(s_ann) in (SomeInstance, ):
            return self.make_instance_wrapper(rtyper, s_ann)
        if hasattr(T, "TO") and type(s_ann) not in (SomeString, ):
            import pdb; pdb.set_trace()
        return T

    def make_instance_wrapper(self, rtyper, s_ann):
        cdef = s_ann.classdef
        importinfo = s_ann.classdef.classdesc.classdict.get('_importinfo_')
        if importinfo is not None:
            return Instance(importinfo.value)
        assert hasattr(cdef, "exportinfo_cls") and hasattr(cdef, "exportinfo_inst")
        if rtyper is not None:
            rtyper.getrepr(s_ann).get_reusable_prebuilt_instance()
        return Instance(self.get_classinfo(s_ann.classdef))

    def externalize_annotation(self, s_thing):
        assert s_thing
        if isinstance(s_thing, annmodel.SomeInstance):
            return self.make_instance_wrapper(None, s_thing)
        return s_thing

def rebuild_annotation(info, bk):
    if isinstance(info, SomeObject):
        return info
    if isinstance(info, Instance):
        classinfo = info.classinfo
        obj = external_class_registry.get_class(classinfo)
    else:
        obj = info
    s_foo = annotationoftype(obj, bk)
    return s_foo


class ImportExportComponent(object):
    """ An ImportExportComponent holds separate compilation data and information about exported
    functions. """
    interface_directory = os.path.join(os.path.dirname(pypy.__file__), "interfaces")
    packages = {}
    translation_key = random.randrange(0, 2**30)

    def __init__(self, name, *args):
        assert name not in ImportExportComponent.packages
        self.name = name
        self.export_tables = None # {}: translation-run-id -> export_table
        self.entry_points = []
        self.update(*args)
        ImportExportComponent.packages[name] = self
        self.dll = None

    def __repr__(self):
        return "<ImportExportComponent %r export_tbls=%r entry_points: %i>" % (self.name,
                self.export_tables, len(self.entry_points))

    def load_from_namespace(self, ns):
        if isinstance(ns, dict):
            dic = ns
        else:
            dic = ns.__dict__
        entrypoints = []
        for item in dic.itervalues():
            if is_exported(item):
                item._component_ = self
                llfnattrs = item._llfnobjattrs_
                if '_name' not in llfnattrs:
                    llfnattrs['_extname'] = get_function_name(item)
                entrypoints.append((item, item._inputtypes_))
            elif isinstance(item, types.ClassType) or isinstance(item, type):
                if getattr(item, '_exported_', None):
                    item._component_ = self
                    item._force_name_ = get_class_name(item)
                    entrypoints += collect_class_entrypoints(item, self)
        self.entry_points.extend(entrypoints)

    def update(self, *args):
        for arg in args:
            self.load_from_namespace(arg)

    def ensure_load(self):
        if self.export_tables is None:
            self.load()

    @property
    def interface_filename(self):
        return os.path.join(self.interface_directory, self.name)

    def load(self):
        if not os.path.exists(self.interface_filename):
            self.export_tables = {}
        else:
            f = file(self.interface_filename, "rb")
            unpickler = ExportTableUnpickler(f)
            self.export_tables = unpickler.load()
            f.close()

    def save(self):
        assert self.export_tables is not None
        if not os.path.exists(self.interface_directory):
            os.mkdir(self.interface_directory)
        f = file(self.interface_filename, "wb")
        pickler = ExportTablePickler(f)
        pickler.dump(self.export_tables)
        f.close()

    def new_table(self):
        self.export_tables = {}
        table = ExportTable()
        self.export_tables[self.translation_key] = table
        return table

    @property
    def table(self):
        self.ensure_load()
        if self.translation_key in self.export_tables:
            return self.export_tables[self.translation_key]
        return self.new_table()

    @property
    def chosen_export_table(self): # XXX add invalidation
        assert len(self.export_tables) == 1
        return self.export_tables[max(self.export_tables.keys())]

    @classmethod
    def search_external_object_info(cls, obj):
        for package in cls.packages.values():
            try:
                return package, package.get_external_object_info(obj)
            except KeyError:
                pass
        raise KeyError("Object %r not found in any export table (loaded: %r)." % (obj, cls.packages.keys()))

    def get_external_object_info(self, obj):
        self.ensure_load()
        if not self.export_tables:
            raise KeyError("No export definitions found.")
        if type(obj) is type: # forcing new style classes
            classinfo = self.chosen_export_table.lookup_class(get_class_name(obj))
            return external_class_registry.get_class(classinfo)
        assert isinstance(obj, type(lambda:None))
        funcname = get_function_name(obj)
        info = self.chosen_export_table.lookup_function(funcname)
        if info is not None:
            return info.get_func()
        raise KeyError("Object %r not found in export table." % (obj, ))

    @classmethod
    def save_all(cls):
        for package in cls.packages.values():
            if package.export_tables is not None:
                package.save()

    def dispose(self):
        os.remove(self.interface_filename)
        del ImportExportComponent.packages[self.name]


class export(object): # based on code from carbonpython, XXX merge
    def __new__(self, *args, **kwds):
        if len(args) == 1 and isinstance(args[0], types.FunctionType):
            func = args[0]
            return export()(func)
        return object.__new__(self, *args, **kwds)

    def __init__(self, *args, **kwds):
        if args == (Ellipsis, ):
            self.inputtypes = Ellipsis
        else:
            self.inputtypes = args
        self.package = kwds.pop("package", None)
        self.force_name = kwds.pop("force_name", None)
        self.return_type = kwds.pop("ret", None)
        if len(kwds) > 0:
            raise TypeError, "unexpected keyword argument: '%s'" % kwds.keys()[0]

    def __call__(self, func):
        func._inputtypes_ = self.inputtypes
        func._package_ = self.package
        llattrs = {'_exported': True}
        if self.force_name:
            llattrs.update({'_name': self.force_name, 'external': 'C'})
        func._llfnobjattrs_ = llattrs
        func._export_ = True
        func._force_virtual_ = True
        func._check_ret_type_ = self.return_type
        return func

def inputtype_to_instance(it):
    obj = synthesize_abstract_class_info(it)
    if isinstance(obj, ClassInfo):
        return Instance(obj)
    return obj

def scimport_forward_reference(obj):
    inputtypes = obj._inputtypes_
    rettype = obj._check_ret_type_
    fi = FunctionInfo(inputtypes, rettype, None, None)
    link_key = obj._llfnobjattrs_.get('_name')
    assert link_key
    fi.link_key = link_key
    return fi


def synthesize_abstract_class_info(obj):
    if obj is None:
        return None
    if type(obj) is not type:
        return obj
    if not obj.__dict__.get('_exported_'):
        return obj
    if not obj.__dict__.get('_abstract_'):
        return None
    if hasattr(obj, "_local_importinfo_"):
        return obj._local_importinfo_
    name = get_class_name(obj)
    bases = obj.__bases__
    base = None
    if bases and bases[0] is not object:
        base = bases[0]
    ci = ClassInfo(synthesize_abstract_class_info(base), [], (), None)
    obj._local_importinfo_ = ci
    ci.vtablename = (obj._component_.name, name)
    for name in obj.__dict__.keys():
        if name.startswith("_"):
            continue
        typ = obj.__dict__[name]
        assert is_exported(typ)
        ci.cls.append(("cls_" + name, name, synthesize_function(typ, obj)))
    return ci


def scimport(obj, iep=None, dynamic=False, forward_ref=False):
    if forward_ref:
        return scimport_forward_reference(obj).get_func(dynamic)
    if iep is not None:
        info = iep.get_external_object_info(obj)
    else:
        iep, info = ImportExportComponent.search_external_object_info(obj)

    return info

def instance_to_lltype(rtyper, val):
    if isinstance(val, Instance):
        return rtyper.getrepr(SomeInstance(rtyper.annotator.bookkeeper.getuniqueclassdef(external_class_registry.get_class(val.classinfo)))).lowleveltype
    return val


def check_package(package_path, checkobj):
    package, objname = package_path.rsplit(".", 1)
    __import__(package)
    mod = sys.modules[package]
    objcheck = getattr(mod, objname)
    assert checkobj is objcheck


def get_function_name(func, package=None, cls=None):
    func_string = func
    if not isinstance(func_string, str):
        func_string = func.func_name
    if package is None and hasattr(func, "_package_"):
        package = func._package_
    if package is None:
        if cls is not None:
            package_path = get_class_name(cls) + "." + func_string
        else:
            package_path = func.__module__ + "." + func_string
            check_package(package_path, func)
    else:
        if package != "":
            package += "."
        package_path = package + func_string
    return "func_" + package_path


def get_class_name(cls):
    if hasattr(cls, "_package_"):
        classname = cls._package_ + cls.__name__
    else:
        classname = cls.__module__ + "." + cls.__name__
        check_package(classname, cls)
    return "class_" + classname


class SeparateModuleFunctionCallable(PseudoHighLevelCallable):
    def __init__(self, link_key, T_args, T_ret, args_s, s_result, dll=False):
        self.link_key = link_key
        self.T_args = T_args
        self.T_ret = T_ret
        self.dll = dll
        assert s_result
        PseudoHighLevelCallable.__init__(self, None, args_s, s_result)

    def __repr__(self):
        return "<SeparateModuleFunctionCallable %r>" % (self.link_key,)

    def compute_rebuilt_args_result(self, bk):
        if hasattr(self, 'args_s_rebuilt') and bk is self.used_bk:
            return
        self.args_s_rebuilt = [rebuild_annotation(s_arg, bk) for s_arg in self.args_s]
        self.s_result_rebuilt = rebuild_annotation(self.s_result, bk)
        self.used_bk = bk


class SeparateModuleFunctionCallableEntry(PseudoHighLevelCallableEntry):
    _type_ = SeparateModuleFunctionCallable

    def compute_result_annotation(self, *args_s):
        bk = self.bookkeeper
        self.instance.compute_rebuilt_args_result(bk)
        s_args_given, s_result = self.instance.args_s_rebuilt, self.instance.s_result_rebuilt
        assert len(s_args_given) == len(args_s)
        for arg_s_1, arg_s_2 in zip(s_args_given, args_s):
            assert arg_s_1.contains(arg_s_2)
        return s_result

    def make_helper(self, rtyper, PFT, link_key, s_args, s_ret):
        def caller(*args): # XXX breaks if the dlopen arguments are changed because the type is unknown
            return rffi.cast(PFT, dlsym(dlopen(lltype.nullptr(rffi.CCHARP.TO), RTLD_GLOBAL | RTLD_NOW), link_key))(*args)
        caller._annspecialcase_ = 'specialize:ll'
        return rtyper.getannmixlevel().delayedfunction(caller, s_args, s_ret, True)

    def specialize_call(self, hop):
        # XXX probably we can retrieve the old graph and make it usable for the llinterpreter?
        args_r = [hop.rtyper.getrepr(s) for s in self.instance.args_s_rebuilt]
        r_res = hop.rtyper.getrepr(self.instance.s_result_rebuilt)
        if self.instance.T_args:
            T_args = [instance_to_lltype(hop.rtyper, i) for i in self.instance.T_args]
            T_ret = instance_to_lltype(hop.rtyper, self.instance.T_ret)
        else:
            T_args = [r.lowleveltype for r in args_r]
            T_ret = r_res.lowleveltype
        vlist = hop.inputargs(*args_r)
        for r_arg, ARGTYPE in zip(args_r, T_args):
            assert r_arg.lowleveltype == ARGTYPE
        assert r_res.lowleveltype == T_ret

        component = None
        lkey = self.instance.link_key
        if isinstance(lkey, tuple):
            component, lkey = lkey
        FT = lltype.FuncType(T_args, T_ret)

        if self.instance.dll:
            fnptr = self.make_helper(hop.rtyper, lltype.Ptr(FT), lkey, [annmodel.lltype_to_annotation(T) for T in T_args], annmodel.lltype_to_annotation(T_ret))
        else:
            fnptr = lltype.functionptr(FT, lkey, component=component, external='C', canraise=True)
        TYPE = lltype.typeOf(fnptr)
        c_func = Constant(fnptr, TYPE)
        hop.exception_is_here()
        return hop.genop('direct_call', [c_func] + vlist, resulttype=r_res)


def is_exported(obj):
    return isinstance(obj, (types.FunctionType, types.UnboundMethodType)) \
           and hasattr(obj, '_inputtypes_')


def collect_class_entrypoints(cls, component):
    from pypy.translator.cli.carbonpython import wrap_method
    entrypoints = []
    for item in cls.__dict__.itervalues():
        if is_exported(item):
            inputtypes = item._inputtypes_
            if inputtypes != Ellipsis:
                inputtypes = (cls,) + item._inputtypes_
                wrapped = wrap_method(item)
                wrapped._meth_wrapper_info_ = (cls, item)
                wrapped._check_ret_type_ = item._check_ret_type_
                wrapped._force_virtual_ = item._force_virtual_
            else:
                wrapped = item
            item._component_ = component
            llfnattrs = item._llfnobjattrs_
            if '_name' not in llfnattrs:
                llfnattrs['_extname'] = get_function_name(item, cls=cls)
            entrypoints.append((wrapped, inputtypes))
    return entrypoints


def unwrap_meth_wrapper(func):
    if hasattr(func, '_meth_wrapper_info_'):
        mwi = func._meth_wrapper_info_
        assert mwi is not None # XXX ctor
        func = mwi[1]
    return func


