#from __future__ import nested_scopes
from pypy.interpreter.gateway import interp2app


class AppTestW_TupleObject:

    def test_is_true(self):
        assert not ()
        assert (5,)
        assert (5,3)

    def test_len(self):
        assert len(()) == 0
        assert len((5,)) == 1
        assert len((5,3,99,1,2,3,4,5,6)) == 9

    def test_getitem(self):
        assert (5,3)[0] == 5
        assert (5,3)[1] == 3
        assert (5,3)[-1] == 3
        assert (5,3)[-2] == 5
        raises(IndexError, "(5,3)[2]")
        raises(IndexError, "(5,)[1]")
        raises(IndexError, "()[0]")

    def test_iter(self):
        t = (5,3,99)
        i = iter(t)
        assert i.next() == 5
        assert i.next() == 3
        assert i.next() == 99
        raises(StopIteration, i.next)

    def test_contains(self):
        t = (5,3,99)
        assert 5 in t
        assert 99 in t
        assert not 11 in t
        assert not t in t

    def test_add(self):
        t0 = ()
        t1 = (5,3,99)
        assert t0 + t0 == t0
        assert t1 + t0 == t1
        assert t1 + t1 == (5,3,99,5,3,99)

    def test_mul(self):
        assert () * 10 == ()
        assert (5,) * 3 == (5,5,5)
        assert (5,2) * 2 == (5,2,5,2)
        assert 2 * (5,) == (5, 5)

    def test_mul_identity(self):
        t = (1,2,3)
        assert (t * 1) is t

    def test_mul_subtype(self):
        class T(tuple): pass
        t = T([1,2,3])
        assert (t * 1) is not t
        assert (t * 1) == t

    def test_getslice_2(self):
        assert (5,2,3)[1:2] == (2,)

    def test_eq(self):
        t0 = ()
        t1 = (5,3,99)
        t2 = (5,3,99)
        t3 = (5,3,99,-1)
        t4 = (5,3,9,1)
        assert not t0 == t1
        assert t0 != t1
        assert t1 == t2
        assert t2 == t1
        assert t3 != t2
        assert not t3 == t2
        assert not t2 == t3
        assert t3 > t4
        assert t2 > t4
        assert t3 > t2
        assert t1 > t0
        assert t0 <= t0
        assert not t0 < t0
        assert t4 >= t0
        assert t3 >= t2
        assert t2 <= t3

    def test_hash(self):
        # check that hash behaves as in 2.4 for at least 31 bits
        assert hash(()) & 0x7fffffff == 0x35d373
        assert hash((12,)) & 0x7fffffff == 0x1cca0557
        assert hash((12,34)) & 0x7fffffff == 0x153e2a41

    def test_getnewargs(self):
        assert  () .__getnewargs__() == ((),)

    def test_repr(self):
        assert repr((1,)) == '(1,)'
        assert repr(()) == '()'
        assert repr((1,2,3)) == '(1, 2, 3)'

    def test_getslice(self):
        assert ('a', 'b', 'c').__getslice__(-17, 2) == ('a', 'b')

    def test_count(self):
        assert ().count(4) == 0
        assert (1, 2, 3, 4).count(3) == 1
        assert (1, 2, 3, 4).count(5) == 0
        assert (1, 1, 1).count(1) == 3

    def test_index(self):
        raises(ValueError, ().index, 4)
        (1, 2).index(1) == 0
        (3, 4, 5).index(4) == 1
        raises(ValueError, (1, 2, 3, 4).index, 5)
        assert (4, 2, 3, 4).index(4, 1) == 3
        assert (4, 4, 4).index(4, 1, 2) == 1
        raises(ValueError, (1, 2, 3, 4).index, 4, 0, 2)


class AppTest_SpecializedTuple(object):
    def setup_class(cls):
        def w_get_specializion(space, w_tuple):
            return space.wrap(w_tuple.tuplestorage.getshape())
        def w_same_specialization(space, w_tuple1, w_tuple2):
            return space.wrap(w_tuple1.tuplestorage.getshape() is w_tuple2.tuplestorage.getshape())
        cls.w_get_specialization = cls.space.wrap(interp2app(w_get_specializion))
        cls.w_same_specialization = cls.space.wrap(interp2app(w_same_specialization))

    def test_ints(self):
        t = (1, 2, 3)
        assert self.get_specialization(t) == "iii"

    def test_floats(self):
        t = (1.1, 1.1, 2.2)
        assert self.get_specialization(t) == "fff"

    def test_bools(self):
        t = (True, False)
        assert self.get_specialization(t) == "bb"
        assert t[0] is True
        assert t[1] is False

    def test_strs(self):
        t = ("a", "b", "c")
        assert self.get_specialization(t) == "sss"

    def test_mixed(self):
        t = (1, True, "a")
        assert self.get_specialization(t) == "ibs"

    def test_add(self):
        t = (1,)
        assert self.get_specialization(t) == "i"
        t = t + t
        assert self.get_specialization(t) == "ii"

    def test_mul(self):
        t = (1,) * 3
        assert self.get_specialization(t) == "iii"
        t = 3 * (1,)
        assert self.get_specialization(t) == "iii"

        x = (1,)
        x *= 3
        assert self.get_specialization(x) == "iii"

        x = 3
        x *= (1,)
        assert self.get_specialization(x) == "iii"

    def test_object(self):
        t = (1, True, object())
        assert self.get_specialization(t) == "ibo"

    def test_specialization(self):
        t = (1,)
        assert self.same_specialization(t, t)

        s = (1, 1)
        t *= 2
        assert self.same_specialization(s, t)

