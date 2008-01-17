from pypy.conftest import gettestobjspace

class AppTestDotnet:
    def setup_class(cls):
        space = gettestobjspace(usemodules=('clr', ))
        cls.space = space

    def test_list_of_valid_namespaces(self):
        import clr
        ns, gen = clr.get_assemblies_info()
        
        assert 'System' in ns
        assert 'System.Collections' in ns
        assert 'System.Runtime' in ns
        assert 'System.Runtime.InteropServices' in ns

    def test_import_hook_simple(self):
        import clr
        import System.Math

        assert System.Math.Abs(-5) == 5
        assert System.Math.Pow(2, 5) == 2**5

        Math = clr.load_cli_class('System', 'Math')
        assert Math is System.Math

        import System
        a = System.Collections.Stack()
        a.Push(3)
        a.Push(44)
        sum = 0
        for i in a:
           sum += i
        assert sum == 3+44

        import System.Collections.ArrayList
        ArrayList = clr.load_cli_class('System.Collections', 'ArrayList')
        assert ArrayList is System.Collections.ArrayList

    def test_ImportError(self):
        def fn():
            import non_existent_module
        raises(ImportError, fn)

    def test_import_twice(self):
        import System
        s1 = System
        import System
        assert s1 is System

    def test_lazy_import(self):
        import System
        System.Runtime.InteropServices # does not raise attribute error

    def test_generic_class_import(self):
        import System.Collections.Generic.List

