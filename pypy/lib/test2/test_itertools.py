from pypy.conftest import gettestobjspace

class AppTestItertools:
    def setup_class(cls):
        cls.space = gettestobjspace()
        cls.w_itertools = cls.space.appexec([], "(): import itertools; return itertools")

    def test_chain(self):
        it = self.itertools.chain([], [1, 2, 3])
        lst = list(it)
        assert lst == [1, 2, 3]
