from pypy.conftest import gettestobjspace

class AppTestGDBM(object):
    def setup_class(cls):
        cls.space = gettestobjspace(usemodules=['gdbm'])
        cls.w_gdbm = cls.space.appexec([], """():
             import gdbm
             return gdbm
        """)

    def test_gdbm_new(self):
        gdbm = self.gdbm
        d = gdbm.new()
        assert isinstance(d, gdbm.gdbm)

    def test_gdbm_store(self):
        gdbm = self.gdbm
        d = gdbm.new()

        b = d.open('file2', 60, 2, 0777)
        assert(b, True)

        i = d.store("one","aaaa", 0)
        assert (i, 0)
        c = d.fetch('one')
        d.close()
