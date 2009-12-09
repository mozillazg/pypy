import sys
import os

import autopath
import py
from pypy import conftest

from pypy.rlib.libffi import CDLL, cast_type_to_ffitype, dlsym, dlopen_global_persistent, RTLD_GLOBAL
from pypy.annotation import model as annmodel
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.rpython.lltypesystem.lltype import Signed, Void
from pypy.translator.driver import TranslationDriver
from pypy.translator.interactive import Translation
from pypy.translator.sepcomp import ImportExportComponent, ExportTable, export, scimport, get_function_name, scimport


def compile(fn, argtypes, gcpolicy="boehm", backendopt=True,
        annotatorpolicy=None, standalone=False, iep_name=''):
    t = Translation(fn, argtypes, gc=gcpolicy, backend="c",
            policy=annotatorpolicy, generatemodule=not standalone, verbose=False, exportpackage=iep_name)
    if not backendopt:
        t.disable(["backendopt_lltype"])
    t.ensure_setup(standalone=standalone)
    t.annotate()
    if conftest.option.view:
        t.view()
    t.source_c()
    if conftest.option.view:
        t.view()
    cbuilder = t.driver.cbuilder
    t.compile_c()
    return cbuilder


def make_main_entrypoint(module_main_function_name, init_func=lambda:None):
    @export(package="", force_name=module_main_function_name, ret=int)
    def dummy():
        return 99
    main_func = scimport(dummy, dynamic=True, forward_ref=True)
    def f_main(argv):
        init_func() # so we can force calls to the constructor 
        so_filename = argv[1]
        dlopen_global_persistent(so_filename)
        print main_func()
        return 0
    return f_main


class TestSeparateCompilation(object):
    def setup_method(self, meth):
        assert not getattr(self, 'packages_to_teardown', [])
        self.packages_to_teardown = []

    def teardown_method(self, meth):
        for package in self.packages_to_teardown:
            try:
                package.dispose()
            except OSError:
                print "Could not dispose package information"
        self.packages_to_teardown = []

    def register_iep(self, package):
        self.packages_to_teardown.append(package)

    def get_iep(self, *args):
        frame = sys._getframe()
        iep = ImportExportComponent(frame.f_back.f_code.co_name, *args)
        self.register_iep(iep)
        return iep

    def test_gather_llinfo(self):
        @export(int, package="")
        def f(x):
            return x + 1
        def entry():
            return 0
        iep = self.get_iep(locals())
        driver = TranslationDriver(overrides={'translation.exportpackage': iep.name})
        driver.setup(entry, [])
        driver.proceed(["database_c"])
        assert iep in ImportExportComponent.packages.values()
        assert len(iep.entry_points) == 1
        assert len(iep.export_tables) == 1
        assert len(iep.export_tables.values()[0].functions) == 1

    def test_export_wrong_rettype(self):
        @export(int, package="", ret=str)
        def f(x):
            return x + 1
        iep = self.get_iep(locals())
        f_main = make_main_entrypoint("module_init")
        py.test.raises(Exception, "compile(f_main, None, standalone=True, iep_name=iep.name)")

    def test_export_wrong_rettype2(self):
        class A:
            _package_ = ""
        class B(A):
            _package_ = ""
        @export(A, package="", ret=B)
        def f(x):
            return x
        iep = self.get_iep(locals())
        f_main = make_main_entrypoint("module_init")
        py.test.raises(Exception, "compile(f_main, None, standalone=True, iep_name=iep.name)")


    def test_import_export(self):
        @export(int, package="")
        def f(x):
            return x + 1
        iep = self.get_iep(locals())
        f_main = make_main_entrypoint("module_init")
        # compile f()+f_main() into an executable
        builder = compile(f_main, None, standalone=True, iep_name=iep.name)

        f_imp = scimport(f, iep)
        @export(force_name="module_init", package="")
        def g(): # equivalent to an init function of a module
            return f_imp(41)
        builder2 = compile(g, [])
        retdata = builder.cmdexec(str(builder2.so_name))
        print repr(retdata)
        # XXX check whether function f_imp is correctly declared
        assert int(retdata) == 42

    def test_shaped_classes(self):
        class foo:
            _exported_ = True
            _inheritable_ = True
            _package_ = ""

            def __init__(self, x):
                self.x = x

            def internal(self): # this method is internal
                return self.x / 2

            @export(package="")
            def bar(self):
                return self.x + 42

        # main part of the program
        @export(int, package="")
        def create_foo(x):
            return foo(x)
        iep = self.get_iep(locals())
        f_main = make_main_entrypoint("module_init", lambda: foo(10).bar() )
        builder = compile(f_main, None, standalone=True, iep_name=iep.name)

        # module part
        create_foo_imp = scimport(create_foo, iep)
        @export(force_name="module_init", package="")
        def g(): # equivalent to an init function of a module
            return create_foo_imp(13).bar()
        builder2 = compile(g, [])
        retdata = builder.cmdexec(str(builder2.so_name))
        assert int(retdata) == 13 + 42

    def test_check_broken_return_type(self):
        class foo(object):
            _exported_ = True
            _package_ = ""

            def __init__(self, x):
                self.x = x

            def internal(self): # this method is internal
                return self.x / 2

            @export(package="")
            def bar(self):
                return self.x + 2

            @export(package="")
            def foo(self):
                return 16 + self.x

        class barinternal(foo):
            def bar(self):
                return self.x + 64

        @export(foo, package="")
        def call_bar_and_foo(x):
            return x.bar() + x.foo() + x.internal()
        iep = self.get_iep(locals())
        f_main = make_main_entrypoint("module_init", lambda: foo(256).bar() + barinternal(-7).bar())
        builder = compile(f_main, None, standalone=True, iep_name=iep.name)
        foo_imported = scimport(foo)
        class baz(foo_imported):
            def __init__(self, x):
                self.y = x
            def bar(self):
                return self # broken type 

        # module part
        bar_caller = scimport(call_bar_and_foo, iep)
        @export(force_name="module_init")
        def g(): # equivalent to an init function of a module
            return bar_caller(baz(4096))
        py.test.raises(annmodel.UnionError, "compile(g, [])")

    def test_avoid_move_up(self):
        py.test.skip("not fixed yet")
        class abstractbase(object):
            pass
        class foo(abstractbase):
            _exported_ = True
            _package_ = ""

            def __init__(self, x):
                self.x = x

            def internal(self): # this method is internal
                return self.x / 2

            @export(package="")
            def bar(self):
                return self.x + 2

            @export(package="")
            def foo(self):
                return 16 + self.x

        class bar(abstractbase):
            def foo(self):
                return 20

        def do_things(x):
            return x.foo()

        def f1(x):
            if x > 5:
                c = foo
            else:
                c = bar
            return do_things(c())

        iep = self.get_iep(locals())
        builder = compile(f, None, standalone=True, iep_name=iep.name)

    def test_inheriting_classes(self):
        class foo(object):
            _exported_ = True
            _package_ = ""

            def __init__(self, x):
                self.x = x

            def internal(self): # this method is internal
                return self.x / 2

            @export(package="", ret=int)
            def bar(self):
                return int(self.x + 2)

            @export(Ellipsis, package="")
            def foo(self, x):
                return 16 + self.x + x

        class barinternal(foo):
            def internal(self):
                return 9
            def bar(self):
                return self.x + 64

        class foo2(foo):
            _exported_ = True
            _package_ = ""

        @export(foo, package="")
        def call_bar_and_foo(x):
            return x.bar() + x.foo(5) + x.internal()
        @export(int, package="")
        def get_internal_instance(x):
            if x > 5:
                return barinternal(42)
            else:
                return foo2(21)
        iep = self.get_iep(locals())
        f_main = make_main_entrypoint("module_init", lambda: foo(256).foo(13) + barinternal(-7).bar())
        builder = compile(f_main, None, standalone=True, iep_name=iep.name)
        foo_imported = scimport(foo)
        foo2_imported = scimport(foo2)
        class baz(foo_imported):
            def __init__(self, x):
                self.y = x
            def bar(self):
                return -self.y + 1024 + self.y * 2

        # module part
        bar_caller = scimport(call_bar_and_foo, iep)
        get_internal_instance_imp = scimport(get_internal_instance)
        @export(force_name="module_init")
        def g(): # equivalent to an init function of a module
            b = baz(4096)
            i = bar_caller(b)
            inst = get_internal_instance_imp(2)
            if isinstance(inst, foo_imported):
                i += 2**16
            if isinstance(inst, foo2_imported):
                i += 2**17
            inst = get_internal_instance_imp(6)
            if isinstance(inst, foo_imported):
                i += 2**18
            if isinstance(inst, foo2_imported):
                i += 2**19
            return i

        builder2 = compile(g, [])
        retdata = builder.cmdexec(str(builder2.so_name))
        assert int(retdata) == 5 + 4096 + 1024 + 16 + 0 + 2**16 + 2**17 + 2**18

    def test_isinstance(self):
        class foo(object):
            _exported_ = True
            _package_ = ""

            def __init__(self, x):
                self.x = x

            @export(package="")
            def bar(self):
                return self.x + 1

        class barinternal(foo):
            def bar(self):
                return self.x + 2

        @export(foo, package="")
        def call_bar_and_foo(x):
            r = 0
            if isinstance(x, foo):
                r += 16
            if isinstance(x, barinternal):
                r += 32
            return x.bar() + r
        iep = self.get_iep(locals())
        f_main = make_main_entrypoint("module_init", lambda: foo(11).bar())
        builder = compile(f_main, None, standalone=True, iep_name=iep.name)
        foo_imported = scimport(foo)
        class baz(foo_imported):
            def bar(self):
                return 4

        # module part
        bar_caller = scimport(call_bar_and_foo, iep)
        @export(force_name="module_init")
        def g(): # equivalent to an init function of a module
            return bar_caller(baz())
        builder2 = compile(g, [])
        retdata = builder.cmdexec(str(builder2.so_name))
        assert int(retdata) == 20

    def test_abstract_classes(self):
        py.test.skip("currently not supported")
        class foo(object):
            _abstract_ = True
            _exported_ = True
            _package_ = ""

            @export(package="", ret=int)
            def bar(self):
                raise NotImplementedError

            @export(int, ret=int, package="")
            def foo(self, x):
                return 16

        class barinternal(foo):
            def __init__(self, x):
                self.z = x
            def internal(self):
                return 9
            def bar(self):
                return self.z + 64

        @export(foo, ret=int, package="")
        def call_bar_and_foo(x):
            return x.bar() + x.foo(5)
        @export(int, ret=foo, package="")
        def get_internal_instance(x):
            if x > 5:
                return barinternal(42)
        iep = self.get_iep(locals())
        f_main = make_main_entrypoint("module_init", lambda: barinternal(-7).bar())
        builder = compile(f_main, None, standalone=True, iep_name=iep.name)
        foo_imported = scimport(foo)
        class baz(foo_imported):
            def __init__(self, x):
                self.y = x
            def bar(self):
                return -self.y + 1024 + self.y * 2

        # module part
        bar_caller = scimport(call_bar_and_foo, iep)
        get_internal_instance_imp = scimport(get_internal_instance)
        @export(force_name="module_init")
        def g(): # equivalent to an init function of a module
            b = baz(4096)
            i = bar_caller(b)
            inst = get_internal_instance_imp(6)
            if isinstance(inst, foo_imported):
                i += 2**16
            return i

        builder2 = compile(g, [])
        retdata = builder.cmdexec(str(builder2.so_name))
        assert int(retdata) == 4096 + 1024 + 16 + 2**16


