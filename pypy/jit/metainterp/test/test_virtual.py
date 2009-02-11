import py
from pypy.rlib.jit import JitDriver, hint
from pypy.jit.hintannotator.policy import StopAtXPolicy
from pyjitpl import oo_meta_interp, get_stats
from test.test_basic import LLJitMixin, OOJitMixin
from pypy.rpython.lltypesystem import lltype, rclass

from vinst import find_sorted_list
import heaptracker


##def test_heaptracker():
##    def f():
##        n = lltype.malloc(NODE)
##        n.value = 42
##        return n
##    res = oo_meta_interp(f, [])
##    assert lltype.typeOf(res) is NODE
##    assert res.value == 42
##    assert get_stats().heaptracker.known_unescaped(res)

def test_find_sorted_list():
    assert find_sorted_list(5, []) == 0
    assert find_sorted_list(4, [(5,)]) == 0
    assert find_sorted_list(5, [(5,)]) == -1
    assert find_sorted_list(6, [(5,)]) == 1
    assert find_sorted_list(2,   [(5,), (6,), (7,)]) == 0
    assert find_sorted_list(5.2, [(5,), (6,), (7,)]) == 1
    assert find_sorted_list(6.5, [(5,), (6,), (7,)]) == 2
    assert find_sorted_list(11,  [(5,), (6,), (7,)]) == 3
    assert find_sorted_list(5, [(5,), (6,), (7,)]) == -3
    assert find_sorted_list(6, [(5,), (6,), (7,)]) == -2
    assert find_sorted_list(7, [(5,), (6,), (7,)]) == -1
    lst = [(j,) for j in range(1, 50, 2)]
    for i in range(50):
        res = find_sorted_list(i, lst)
        if i % 2 == 0:
            assert res == i // 2
        else:
            assert res == (i // 2) - (50 // 2)


class VirtualTests:
    def _freeze_(self):
        return True

    def test_virtualized(self):
        myjitdriver = JitDriver(greens = [], reds = ['n', 'node'])
        def f(n):
            node = self._new()
            node.value = 0
            node.extra = 0
            while n > 0:
                myjitdriver.jit_merge_point(n=n, node=node)
                next = self._new()
                next.value = node.value + n
                next.extra = node.extra + 1
                node = next
                n -= 1
            return node.value * node.extra
        assert f(10) == 55 * 10
        res = self.meta_interp(f, [10], exceptions=False)
        assert res == 55 * 10
        assert len(get_stats().loops) == 1
        get_stats().check_loops(new=0, new_with_vtable=0,
                                getfield_int=0, getfield_ptr=0,
                                setfield_int=0, setfield_ptr=0)

    def test_virtualized_2(self):
        myjitdriver = JitDriver(greens = [], reds = ['n', 'node'])
        def f(n):
            node = self._new()
            node.value = 0
            node.extra = 0
            while n > 0:
                myjitdriver.jit_merge_point(n=n, node=node)
                next = self._new()
                next.value = node.value
                next.value += n
                next.extra = node.extra
                next.extra += 1
                next.extra += 1
                next.extra += 1
                node = next
                n -= 1
            return node.value * node.extra
        res = self.meta_interp(f, [10], exceptions=False)
        assert res == 55 * 30
        assert len(get_stats().loops) == 1
        get_stats().check_loops(new=0, new_with_vtable=0,
                                getfield_int=0, getfield_ptr=0,
                                setfield_int=0, setfield_ptr=0)

    def test_nonvirtual_obj_delays_loop(self):
        myjitdriver = JitDriver(greens = [], reds = ['n', 'node'])
        node0 = self._new()
        node0.value = 10
        def f(n):
            node = node0
            while True:
                myjitdriver.jit_merge_point(n=n, node=node)
                i = node.value
                if i >= n:
                    break
                node = self._new()
                node.value = i * 2
            return node.value
        res = self.meta_interp(f, [500], exceptions=False)
        assert res == 640
        # The only way to make an efficient loop (in which the node is
        # virtual) is to keep the first iteration out of the residual loop's
        # body.  Indeed, the initial value 'node0' cannot be passed inside
        # the loop as a virtual.  It's hard to test that this is what occurred,
        # though.
        assert len(get_stats().loops) == 1
        get_stats().check_loops(new=0, new_with_vtable=0,
                                getfield_int=0, getfield_ptr=0,
                                setfield_int=0, setfield_ptr=0)

    def test_two_loops_with_virtual(self):
        myjitdriver = JitDriver(greens = [], reds = ['n', 'node'])
        def f(n):
            node = self._new()
            node.value = 0
            node.extra = 0
            while n > 0:
                myjitdriver.jit_merge_point(n=n, node=node)
                next = self._new()
                next.value = node.value + n
                next.extra = node.extra + 1
                if next.extra == 4:
                    next.value += 100
                    next.extra = 0
                node = next
                n -= 1
            return node.value
        res = self.meta_interp(f, [10], exceptions=False)
        assert res == 255
        assert len(get_stats().loops) == 2
        get_stats().check_loops(new=0, new_with_vtable=0,
                                getfield_int=0, getfield_ptr=0,
                                setfield_int=0, setfield_ptr=0)

    def test_two_loops_with_escaping_virtual(self):
        myjitdriver = JitDriver(greens = [], reds = ['n', 'node'])
        def externfn(node):
            return node.value * 2
        def f(n):
            node = self._new()
            node.value = 0
            node.extra = 0
            while n > 0:
                myjitdriver.jit_merge_point(n=n, node=node)
                next = self._new()
                next.value = node.value + n
                next.extra = node.extra + 1
                if next.extra == 4:
                    next.value = externfn(next)
                    next.extra = 0
                node = next
                n -= 1
            return node.value
        res = self.meta_interp(f, [10], policy=StopAtXPolicy(externfn),
                                        exceptions=False)
        assert res == f(10)
        assert len(get_stats().loops) == 2
        get_stats().check_loops(**{self._new_op: 1})
        get_stats().check_loops(int_mul=0, call__4=1)

    def test_virtual_if_unescaped_so_far(self):
        class Foo(object):
            def __init__(self, x, y):
                self.x = x
                self.y = y

        def f(n):
            foo = Foo(n, 0)
            while foo.x > 0:
                foo.y += foo.x
                foo.x -= 1
            return foo.y

        res = self.meta_interp(f, [10], exceptions=False)
        assert res == 55
        py.test.skip("unsure yet if we want to be clever about this")
        get_stats().check_loops(getfield_int=0, setfield_int=0)

    def test_two_virtuals(self):
        class Foo(object):
            def __init__(self, x, y):
                self.x = x
                self.y = y

        def f(n):
            prev = Foo(n, 0)
            n -= 1
            while n >= 0:
                foo = Foo(n, 0)
                foo.x += prev.x
                prev = foo
                n -= 1
            return prev.x

        res = self.meta_interp(f, [12], exceptions=False)
        assert res == 78

    def test_both_virtual_and_field_variable(self):
        class Foo(object):
            pass
        def f(n):
            while n >= 0:
                foo = Foo()
                foo.n = n
                if n < 10:
                    break
                n = foo.n - 1
            return n

        res = self.meta_interp(f, [20], exceptions=False)
        assert res == 9


##class TestOOtype(VirtualTests, OOJitMixin):
##    _new = staticmethod(ootype.new)

# ____________________________________________________________
# Run 1: all the tests instantiate a real RPython class

class MyClass:
    pass

class TestLLtype_Instance(VirtualTests, LLJitMixin):
    _new_op = 'new_with_vtable'
    @staticmethod
    def _new():
        return MyClass()

# ____________________________________________________________
# Run 2: all the tests use lltype.malloc to make a NODE

NODE = lltype.GcStruct('NODE', ('value', lltype.Signed),
                               ('extra', lltype.Signed))

class TestLLtype_NotObject(VirtualTests, LLJitMixin):
    _new_op = 'new'
    @staticmethod
    def _new():
        return lltype.malloc(NODE)

# ____________________________________________________________
# Run 3: all the tests use lltype.malloc to make a NODE2
# (same as Run 2 but it is part of the OBJECT hierarchy)

NODE2 = lltype.GcStruct('NODE2', ('parent', rclass.OBJECT),
                                 ('value', lltype.Signed),
                                 ('extra', lltype.Signed))

vtable2 = lltype.malloc(rclass.OBJECT_VTABLE, immortal=True)
heaptracker.set_testing_vtable_for_gcstruct(NODE2, vtable2)

class TestLLtype_Object(VirtualTests, LLJitMixin):
    _new_op = 'new_with_vtable'
    @staticmethod
    def _new():
        p = lltype.malloc(NODE2)
        p.parent.typeptr = vtable2
        return p

# ____________________________________________________________
