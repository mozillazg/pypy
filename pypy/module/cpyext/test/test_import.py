import py

from pypy.module.cpyext.test.test_api import BaseApiTest

class TestImport(BaseApiTest):
    def test_import(self, space, api):
        # failing because we dont have a caller
        skip("Fails currently, dont know how to fix")
        pdb = api.PyImport_Import(space.wrap("pdb"))
        assert pdb
        assert pdb.get("pm")
