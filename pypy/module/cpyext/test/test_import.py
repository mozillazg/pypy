from pypy.module.cpyext.test.test_api import BaseApiTest
from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase

class TestImport(BaseApiTest):
    def test_import(self, space, api):
        # failing because we dont have a caller
        skip("Fails currently, dont know how to fix")
        pdb = api.PyImport_Import(space.wrap("pdb"))
        assert pdb
        assert pdb.get("pm")

class AppTestImportLogic(AppTestCpythonExtensionBase):
    def test_import_logic(self):
        path = self.import_module(name='foo', load_it=False)
        import sys
        sys.path.append(path)
        import foo
        assert foo.fooType

