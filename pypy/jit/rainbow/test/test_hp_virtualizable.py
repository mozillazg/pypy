import py
from pypy.jit.rainbow.test.test_portal import PortalTest, P_OOPSPEC
from pypy.jit.rainbow.test.test_interpreter import StopAtXPolicy
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython.lltypesystem.rvirtualizable import VABLERTIPTR
from pypy.rlib.jit import hint
from pypy.rlib.jit import JitDriver, hint, JitHintError
from pypy.rlib.rarithmetic import intmask
from pypy.jit.rainbow.test import test_hotpath


S = lltype.GcStruct('s', ('a', lltype.Signed), ('b', lltype.Signed))
PS = lltype.Ptr(S)

XY = lltype.GcForwardReference()
GETTER = lambda STRUC: lltype.Ptr(lltype.FuncType([lltype.Ptr(STRUC)],
                                                  lltype.Signed))
SETTER = lambda STRUC: lltype.Ptr(lltype.FuncType([lltype.Ptr(STRUC),
                                                  lltype.Signed],
                                                 lltype.Void))

def getset(name):
    def get(obj):
        access = obj.vable_access
        if access:
            return getattr(access, 'get_'+name)(obj)
        else:
            return getattr(obj, name)
    get.oopspec = 'vable.get_%s(obj)' % name
    def set(obj, value):
        access = obj.vable_access
        if access:
            return getattr(access, 'set_'+name)(obj, value)
        else:
            return setattr(obj, name, value)
    set.oopspec = 'vable.set_%s(obj, value)' % name
    return get, set

XP = lltype.GcForwardReference()
PGETTER = lambda XP: lltype.Ptr(lltype.FuncType([lltype.Ptr(XP)], PS))
PSETTER = lambda XP: lltype.Ptr(lltype.FuncType([lltype.Ptr(XP), PS],
                                   lltype.Void))

XY_ACCESS = lltype.Struct('xy_access',
                          ('get_x', GETTER(XY)),
                          ('set_x', SETTER(XY)),
                          ('get_y', GETTER(XY)),
                          ('set_y', SETTER(XY)),
                          hints = {'immutable': True},
                          adtmeths = {'redirected_fields': ('x', 'y')}
                          )


XP_ACCESS = lltype.Struct('xp_access',
                          ('get_x', GETTER(XP)),
                          ('set_x', SETTER(XP)),
                          ('get_p', PGETTER(XP)),
                          ('set_p', PSETTER(XP)),
                          hints = {'immutable': True},
                          adtmeths = {'redirected_fields': ('x', 'p')}
                          )

XY.become(lltype.GcStruct('xy',
                          ('vable_base', llmemory.Address),
                          ('vable_rti', VABLERTIPTR),
                          ('vable_access', lltype.Ptr(XY_ACCESS)),
                          ('x', lltype.Signed),
                          ('y', lltype.Signed),
                          hints = {'virtualizable': True},
                          adtmeths = {'ACCESS': XY_ACCESS},
              ))

E = lltype.GcStruct('e', ('xy', lltype.Ptr(XY)),
                         ('w',  lltype.Signed))
xy_get_x, xy_set_x = getset('x')
xy_get_y, xy_set_y = getset('y')


XP.become(lltype.GcStruct('xp',
                          ('vable_base', llmemory.Address),
                          ('vable_rti', VABLERTIPTR),                     
                          ('vable_access', lltype.Ptr(XP_ACCESS)),
                          ('x', lltype.Signed),
                          ('p', PS),
                          hints = {'virtualizable': True},
                          adtmeths = {'ACCESS': XP_ACCESS},
              ))
xp_get_x, xp_set_x = getset('x')
xp_get_p, xp_set_p = getset('p')

E2 = lltype.GcStruct('e', ('xp', lltype.Ptr(XP)),
                         ('w',  lltype.Signed))

PQ = lltype.GcForwardReference()
PQ_ACCESS = lltype.Struct('pq_access',
                          ('get_p', PGETTER(PQ)),
                          ('set_p', PSETTER(PQ)),
                          ('get_q', PGETTER(PQ)),
                          ('set_q', PSETTER(PQ)),
                          hints = {'immutable': True},
                          adtmeths = {'redirected_fields': ('p', 'q')}
                          )

PQ.become(lltype.GcStruct('pq',
                          ('vable_base', llmemory.Address),
                          ('vable_rti', VABLERTIPTR),                     
                          ('vable_access', lltype.Ptr(PQ_ACCESS)),
                          ('p', PS),
                          ('q', PS),
                          hints = {'virtualizable': True},
                          adtmeths = {'ACCESS': PQ_ACCESS},
              ))
pq_get_p, pq_set_p = getset('p')
pq_get_q, pq_set_q = getset('q')

E3 = lltype.GcStruct('e', ('pq', lltype.Ptr(PQ)),
                         ('w',  lltype.Signed))



class TestVirtualizableExplicit(test_hotpath.HotPathTest):
    type_system = "lltype"

    def test_simple(self):
        myjitdriver = JitDriver(greens = [],
                                reds = ['i', 'tot', 'xy'])

        def f(xy):
            tot = 0
            i = 1024
            while i:
                i >>= 1
                x = xy_get_x(xy)
                y = xy_get_y(xy)
                tot += x+y
                myjitdriver.jit_merge_point(tot=tot, i=i, xy=xy)
                myjitdriver.can_enter_jit(tot=tot, i=i, xy=xy)
            return tot

        def main(x, y):
            xy = lltype.malloc(XY)
            xy.vable_access = lltype.nullptr(XY_ACCESS)
            xy.x = x
            xy.y = y
            return f(xy)

        res = self.run(main, [20, 22], 2, policy=P_OOPSPEC)
        assert res == 42 * 11
        self.check_insns_in_loops(getfield=0)
        return
        # XXX port the rest
        if self.on_llgraph:
            residual_graph = self.get_residual_graph()
            inputargs = residual_graph.startblock.inputargs
            assert len(inputargs) == 3
            assert ([v.concretetype for v in inputargs] ==
                    [lltype.Ptr(XY), lltype.Signed, lltype.Signed])

    def test_simple_set(self):
        myjitdriver = JitDriver(greens = [],
                                reds = ['i', 'tot', 'xy'])
   
        def f(xy):
            tot = 0
            i = 1024
            while i:
                i >>= 1
                x = xy_get_x(xy)
                xy_set_y(xy, 1)
                y = xy_get_y(xy)
                tot += x+y
                myjitdriver.jit_merge_point(tot=tot, i=i, xy=xy)
                myjitdriver.can_enter_jit(tot=tot, i=i, xy=xy)
            return tot

        def main(x, y):
            xy = lltype.malloc(XY)
            xy.vable_access = lltype.nullptr(XY_ACCESS)
            xy.x = x
            xy.y = y
            return f(xy)

        res = self.run(main, [20, 22], 2, policy=P_OOPSPEC)
        assert res == 21 * 11
        self.check_insns_in_loops(getfield=0)
        if self.on_llgraph:
            residual_graph = self.get_residual_graph()
            inputargs = residual_graph.startblock.inputargs
            assert len(inputargs) == 5
            assert ([v.concretetype for v in inputargs[-3:]] ==
                    [lltype.Ptr(XY), lltype.Signed, lltype.Signed])

    def test_set_effect(self):
        myjitdriver = JitDriver(greens = [],
                                reds = ['i', 'tot', 'xy'])

        def f(xy):
            tot = 0
            i = 1024
            while i:
                i >>= 1
                x = xy_get_x(xy)
                xy_set_y(xy, i)
                y = xy_get_y(xy)
                v = x + y
                tot += v
                myjitdriver.jit_merge_point(tot=tot, i=i, xy=xy)
                myjitdriver.can_enter_jit(tot=tot, i=i, xy=xy)
            return tot

        def main(x, y):
            xy = lltype.malloc(XY)
            xy.vable_access = lltype.nullptr(XY_ACCESS)
            xy.x = x
            xy.y = y
            v = f(xy)
            return v + xy.y

        res = self.run(main, [20, 22], 2)
        assert res == main(20, 22)
        self.check_insns_in_loops(getfield=0)
        if self.on_llgraph:
            residual_graph = self.get_residual_graph()
            inputargs = residual_graph.startblock.inputargs
            assert len(inputargs) == 5
            assert ([v.concretetype for v in inputargs[-3:]] ==
                    [lltype.Ptr(XY), lltype.Signed, lltype.Signed])

    def test_simple_escape(self):
        myjitdriver = JitDriver(greens = [],
                                reds = ['i', 'xy', 'e'])

        def f(e, xy):
            i = 1024
            while i:
                i >>= 1
                xy_set_y(xy, xy_get_y(xy) + 3)
                e.xy = xy
                myjitdriver.jit_merge_point(i=i, xy=xy, e=e)
                myjitdriver.can_enter_jit(i=i, xy=xy, e=e)
            return e.xy.y

        def main(x, y):
            xy = lltype.malloc(XY)
            xy.vable_access = lltype.nullptr(XY_ACCESS)
            xy.x = x
            xy.y = y
            e = lltype.malloc(E)
            f(e, xy)
            return e.xy.x+e.xy.y

        res = self.run(main, [20, 22], 2)
        assert res == main(20, 22)
        self.check_insns_in_loops(getfield=0)
        if self.on_llgraph:
            residual_graph = self.get_residual_graph()
            inputargs = residual_graph.startblock.inputargs
            assert len(inputargs) == 5
            assert ([v.concretetype for v in inputargs[-4:]] ==
                [lltype.Ptr(XY), lltype.Signed, lltype.Signed, lltype.Ptr(E)])

    def test_simple_return_it(self):
        myjitdriver = JitDriver(greens = [],
                                reds = ['which', 'i', 'xy1', 'xy2'])

        def f(which, xy1, xy2):
            i = 1024
            while i:
                i >>= 1
                xy_set_y(xy1, xy_get_y(xy1) + 3)
                xy_set_y(xy2, xy_get_y(xy2) + 7)
                myjitdriver.jit_merge_point(i=i, which=which, xy1=xy1, xy2=xy2)
                myjitdriver.can_enter_jit(i=i, which=which, xy1=xy1, xy2=xy2)
            if which == 1:
                return xy1
            else:
                return xy2

        def main(which, x, y):
            xy1 = lltype.malloc(XY)
            xy1.vable_access = lltype.nullptr(XY_ACCESS)
            xy2 = lltype.malloc(XY)
            xy2.vable_access = lltype.nullptr(XY_ACCESS)
            xy1.x = x
            xy1.y = y
            xy2.x = y
            xy2.y = x
            xy = f(which, xy1, xy2)
            assert xy is xy1 or xy is xy2
            return xy.x+xy.y

        res = self.run(main, [1, 20, 22], 2)
        assert res == main(1, 20, 22)
        self.check_insns_in_loops(getfield=0, setfield=0)

        # also run the test with a threshold of 1 to check if the return
        # path (taken only once) is compiled correctly
        res = self.run(main, [0, 20, 22], threshold=1)
        assert res == main(0, 20, 22)
        self.check_insns_in_loops(getfield=0, setfield=0)

    def test_simple_aliasing(self):
        myjitdriver = JitDriver(greens = [],
                                reds = ['i', 'xy1', 'xy2', 'res', 'which'])

        def f(which, xy1, xy2):
            xy_set_y(xy1, xy_get_y(xy1) + 3)
            xy_set_y(xy2, xy_get_y(xy2) + 3)
            if which == 1:
                return xy1
            else:
                return xy2

        def main(which, x, y):
            xy1 = lltype.malloc(XY)
            xy1.vable_access = lltype.nullptr(XY_ACCESS)
            xy2 = lltype.malloc(XY)
            xy2.vable_access = lltype.nullptr(XY_ACCESS)
            xy1.x = x
            xy1.y = y
            xy2.x = y
            xy2.y = x
            i = 1024
            while i:
                i >>= 1
                xy = f(which, xy1, xy2)
                assert xy is xy1 or xy is xy2
                res = xy.x+xy.y
                myjitdriver.jit_merge_point(i=i, xy1=xy1, xy2=xy2, res=res, which=which)
                myjitdriver.can_enter_jit(i=i, xy1=xy1, xy2=xy2, res=res, which=which)
            return res

        res = self.run(main, [1, 20, 22], 2)
        assert res == main(1, 20, 22)
        self.check_insns_in_loops(getfield=0)
        res = self.run(main, [0, 20, 22], 2)
        assert res == main(0, 20, 22)
        self.check_insns_in_loops(getfield=0)

    def test_simple_construct_no_escape(self):
        myjitdriver = JitDriver(greens = [],
                                reds = ['i', 'tot', 'x', 'y'])

        def f(x, y):
            xy = lltype.malloc(XY)
            xy.vable_access = lltype.nullptr(XY_ACCESS)
            xy.x = x
            xy.y = y
            x = xy_get_x(xy)
            y = xy_get_y(xy)
            return x+y

        def main(x, y):
            tot = 0
            i = 1024
            while i:
                i >>= 1
                tot += f(x, y)
                myjitdriver.jit_merge_point(tot=tot, i=i, x=x, y=y)
                myjitdriver.can_enter_jit(tot=tot, i=i, x=x, y=y)
            return tot

        res = self.run(main, [20, 22], 2)
        assert res == 42 * 11
        self.check_insns_in_loops({'int_add': 2, 'int_is_true': 1,
                                   'int_rshift': 1})

    def test_simple_construct_escape(self):
        myjitdriver = JitDriver(greens = [],
                                reds = ['x', 'y'])
   
        def f(x, y):
            myjitdriver.jit_merge_point(x=x, y=y)
            myjitdriver.can_enter_jit(x=x, y=y)
            xy = lltype.malloc(XY)
            xy.vable_access = lltype.nullptr(XY_ACCESS)
            xy.x = x
            xy.y = y
            return xy

        def main(x, y):
            xy = f(x, y)
            return xy_get_x(xy)+xy_get_y(xy)

        assert main(20, 22) == 42
        res = self.run(main, [20, 22], 2)
        assert res == 42
        self.check_nothing_compiled_at_all()

        res = self.run(main, [20, 22], threshold=1)
        assert res == 42
        self.check_insns(malloc=1)

    def test_pass_in_construct_another_and_escape(self):
        py.test.skip("in-progress")
        myjitdriver = JitDriver(greens = [],
                                reds = ['i', 'xy', 'x', 'y'])
   
        def f(x, y):
            i = 1024
            while i:
                i >>= 1
                xy = lltype.malloc(XY)
                xy.vable_access = lltype.nullptr(XY_ACCESS)
                xy.x = x
                xy.y = y
                x = xy_get_x(xy)
                y = xy_get_y(xy)            
                myjitdriver.jit_merge_point(xy=xy, i=i, x=x, y=y)
                myjitdriver.can_enter_jit(xy=xy, i=i, x=x, y=y)
            return xy

        def main(x, y):
            xy = f(x, y)
            return xy_get_x(xy)+xy_get_y(xy)

        assert main(20, 22) == 42
        res = self.run(main, [20, 22], 2)
        assert res == 42
        self.check_insns_in_loops(getfield=0)

    def test_simple_with_struct(self):
        myjitdriver = JitDriver(greens = [],
                                reds = ['i', 'tot', 'xp'])

        def f(xp):
            tot = 0
            i = 1024
            while i:
                i >>= 1
                x = xp_get_x(xp)
                p = xp_get_p(xp)
                res = x+p.a+p.b
                tot += res
                myjitdriver.jit_merge_point(tot=tot, i=i, xp=xp)
                myjitdriver.can_enter_jit(tot=tot, i=i, xp=xp)
            return tot

        def main(x, a, b):
            xp = lltype.malloc(XP)
            xp.vable_access = lltype.nullptr(XP_ACCESS)
            xp.x = x
            s = lltype.malloc(S)
            s.a = a
            s.b = b
            xp.p = s
            return f(xp)

        res = self.run(main, [20, 10, 12], 2)
        assert res == 42 * 11
        self.check_insns_in_loops(getfield=2)    

    def test_simple_with_setting_struct(self):
        myjitdriver = JitDriver(greens = [],
                                reds = ['i', 'tot', 'xp', 's', 'x'])
   
        def f(xp, s):
            tot = 0
            i = 1024
            while i:
                i >>= 1
                xp_set_p(xp, s)
                x = xp_get_x(xp)
                p = xp_get_p(xp)
                p.b = p.b*2
                v = x+p.a+p.b
                tot += v+xp.p.b
                myjitdriver.jit_merge_point(tot=tot, i=i, xp=xp, s=s, x=x)
                myjitdriver.can_enter_jit(tot=tot, i=i, xp=xp, s=s, x=x)
            return tot

        def main(x, a, b):
            xp = lltype.malloc(XP)
            xp.vable_access = lltype.nullptr(XP_ACCESS)
            xp.x = x
            s = lltype.malloc(S)
            s.a = a
            s.b = b
            v = f(xp, s)
            return v+xp.p.b

        res = self.run(main, [20, 10, 3], 2)
        assert res == main(20, 10, 3)
        self.check_insns_in_loops(getfield=4)

    def test_simple_with_setting_new_struct(self):
        myjitdriver = JitDriver(greens = [],
                                reds = ['i', 'tot', 'xp', 'a', 'b'])
   
        def f(xp, a, b):
            tot = 0
            i = 1024
            while i:
                i >>= 1
                s = lltype.malloc(S)
                s.a = a
                s.b = b
                xp_set_p(xp, s)            
                p = xp_get_p(xp)
                p.b = p.b*2
                x = xp_get_x(xp)
                v = x+p.a+p.b
                tot += v
                myjitdriver.jit_merge_point(tot=tot, i=i, xp=xp, a=a, b=b)
                myjitdriver.can_enter_jit(tot=tot, i=i, xp=xp, a=a, b=b)
            return tot

        def main(x, a, b):
            xp = lltype.malloc(XP)
            xp.vable_access = lltype.nullptr(XP_ACCESS)
            xp.x = x
            v = f(xp, a, b)
            return v+xp.p.b

        res = self.run(main, [20, 10, 3], 2)
        assert res == main(20, 10, 3)
        self.check_insns_in_loops(getfield=0, malloc=0)


    def test_simple_constr_with_setting_new_struct(self):
        myjitdriver = JitDriver(greens = [],
                                reds = ['i', 'xp', 'x', 'a', 'b'])

        def f(x, a, b):
            i = 1024
            while i:
                i >>= 1
                #
                xp = lltype.malloc(XP)
                xp.vable_access = lltype.nullptr(XP_ACCESS)
                xp.x = x
                s = lltype.malloc(S)
                s.a = a
                s.b = b            
                xp_set_p(xp, s)            
                p = xp_get_p(xp)
                p.b = p.b*2
                x = xp_get_x(xp)
                #
                myjitdriver.jit_merge_point(xp=xp, i=i, x=x, a=a, b=b)
                myjitdriver.can_enter_jit(xp=xp, i=i, x=x, a=a, b=b)
            return xp

        def main(x, a, b):
            xp = f(x, a, b)
            return xp.x+xp.p.a+xp.p.b+xp.p.b

        res = self.run(main, [20, 10, 3], 2)
        assert res == 42
        self.check_insns_in_loops(getfield=0, malloc=0)

        # run again with threshold 1 to get the return generated too
        res = self.run(main, [20, 10, 3], 1)
        assert res == 42
        self.check_insns_in_loops(getfield=0, malloc=0)

    def test_simple_read(self):
        myjitdriver = JitDriver(greens = [],
                                reds = ['i', 'tot', 'e'])

        def f(e):
            tot = 0
            i = 1024
            while i:
                i >>= 1
                xy = e.xy
                xy_set_y(xy, xy_get_y(xy) + 3)
                v = xy_get_x(xy)*2
                tot += v
                myjitdriver.jit_merge_point(tot=tot, i=i, e=e)
                myjitdriver.can_enter_jit(tot=tot, i=i, e=e)
            return tot

        def main(x, y):
            xy = lltype.malloc(XY)
            xy.vable_access = lltype.nullptr(XY_ACCESS)
            xy.x = x
            xy.y = y
            e = lltype.malloc(E)
            e.xy = xy
            v = f(e)
            return v + e.xy.x+e.xy.y

        res = self.run(main, [20, 22], 2)
        assert res == main(20, 22)
        self.check_insns_in_loops(getfield=3)

    def test_simple_escape_through_vstruct(self):
        myjitdriver = JitDriver(greens = [],
                                reds = ['i', 'e', 'x', 'y'])

        def f(x, y):
            i = 1024
            while i:
                i >>= 1
                #
                xy = lltype.malloc(XY)
                xy.vable_access = lltype.nullptr(XY_ACCESS)
                xy.x = x
                xy.y = y
                e = lltype.malloc(E)
                e.xy = xy
                y = xy_get_y(xy)
                newy = 2*y
                xy_set_y(xy, newy)
                #
                myjitdriver.jit_merge_point(e=e, i=i, x=x, y=y)
                myjitdriver.can_enter_jit(e=e, i=i, x=x, y=y)
            return e

        def main(x, y):
            e = f(x, y)
            return e.xy.x+e.xy.y

        res = self.run(main, [20, 11], 2)
        assert res == 42
        self.check_insns_in_loops(getfield=0, malloc=0)

        res = self.run(main, [20, 11], threshold=1)
        assert res == 42
        self.check_insns_in_loops(getfield=0, malloc=0)

    def test_residual_doing_nothing(self):
        myjitdriver = JitDriver(greens = [],
                                reds = ['xy', 'i', 'res'])

        class Counter:
            counter = 0
        glob = Counter()

        def g(xy):
            glob.counter += 1

        def f(xy):
            i = 1024
            while i > 0:
                i >>= 1
                g(xy)
                res = xy.x + 1
                myjitdriver.jit_merge_point(xy=xy, res=res, i=i)
                myjitdriver.can_enter_jit(xy=xy, res=res, i=i)
            return res

        def main(x, y):
            xy = lltype.malloc(XY)
            xy.vable_access = lltype.nullptr(XY_ACCESS)
            xy.x = x
            xy.y = y
            v = f(xy)
            return v - glob.counter

        res = self.run(main, [2, 20], threshold=2,
                       policy=StopAtXPolicy(g))
        assert res == 3 - 11
        self.check_insns_in_loops(direct_call=1)

    def test_late_residual_red_call(self):
        myjitdriver = JitDriver(greens = [],
                                reds = ['e', 'z', 'i', 'res'])

        def g(e):
            xy = e.xy
            y = xy_get_y(xy)
            e.w = y

        def f(e, z):
            i = 1024
            while i > 0:
                i >>= 1
                #
                xy = e.xy
                y = xy_get_y(xy)
                newy = 2*y
                xy_set_y(xy, newy)
                if y:
                    res = z*2
                else:
                    res = z*3
                g(e)
                #
                myjitdriver.jit_merge_point(e=e, z=z, res=res, i=i)
                myjitdriver.can_enter_jit(e=e, z=z, res=res, i=i)
            return res

        def main(x, y, z):
            xy = lltype.malloc(XY)
            xy.vable_access = lltype.nullptr(XY_ACCESS)
            xy.x = x
            xy.y = y
            e = lltype.malloc(E)
            e.xy = xy
            f(e, z)
            return e.w

        res = self.run(main, [0, 21, 11], threshold=2,
                       policy=StopAtXPolicy(g))
        assert res == main(0, 21, 11)

        res = self.run(main, [0, 21, 11], threshold=1,
                       policy=StopAtXPolicy(g))
        assert res == main(0, 21, 11)

    def test_residual_red_call(self):
        myjitdriver = JitDriver(greens = [],
                                reds = ['e', 'i', 'res'])

        def g(e):
            xy = e.xy
            y = xy_get_y(xy)
            e.w = y        

        def f(e):
            i = 1024
            while i > 0:
                i >>= 1
                #
                xy = e.xy
                y = xy_get_y(xy)
                newy = 2*y
                xy_set_y(xy, newy)
                g(e)
                res = xy.x
                #
                myjitdriver.jit_merge_point(e=e, res=res, i=i)
                myjitdriver.can_enter_jit(e=e, res=res, i=i)
            return res

        def main(x, y):
            xy = lltype.malloc(XY)
            xy.vable_access = lltype.nullptr(XY_ACCESS)
            xy.x = x
            xy.y = y
            e = lltype.malloc(E)
            e.xy = xy
            v = f(e)
            return v+e.w

        res = self.run(main, [2, 20], threshold=2,
                       policy=StopAtXPolicy(g))
        assert res == main(2, 20)

        res = self.run(main, [2, 20], threshold=1,
                       policy=StopAtXPolicy(g))
        assert res == main(2, 20)

    def test_force_in_residual_red_call(self):
        myjitdriver = JitDriver(greens = [],
                                reds = ['e', 'a', 'b', 'i', 'res'])

        def g(e):
            xp = e.xp
            p = xp_get_p(xp)
            x = xp_get_x(xp)
                
            e.w = p.a + p.b + x

        def f(e, a, b):
            i = 1024
            while i > 0:
                i >>= 1
                #
                xp = e.xp
                s = lltype.malloc(S)
                s.a = a
                s.b = b

                xp_set_p(xp, s)

                x = xp_get_x(xp)
                newx = 2*x
                xp_set_x(xp, newx)
                g(e)            
                res = xp.x
                #
                myjitdriver.jit_merge_point(e=e, a=a, b=b, res=res, i=i)
                myjitdriver.can_enter_jit(e=e, a=a, b=b, res=res, i=i)
            return res
            
        def main(a, b, x):
            xp = lltype.malloc(XP)
            xp.vable_access = lltype.nullptr(XP_ACCESS)
            xp.x = x
            xp.p = lltype.nullptr(S)
            e = lltype.malloc(E2)
            e.xp = xp
            f(e, a, b)
            return e.w

        res = self.run(main, [2, 20, 10], threshold=2,
                       policy=StopAtXPolicy(g))
        assert res == main(2, 20, 10)

        res = self.run(main, [2, 20, 10], threshold=1,
                       policy=StopAtXPolicy(g))
        assert res == main(2, 20, 10)

    def test_force_multiple_reads_residual_red_call(self):
        myjitdriver = JitDriver(greens = [],
                                reds = ['e', 'a', 'b', 'i', 'res'])

        def g(e):
            xp = e.xp
            p1 = xp_get_p(xp)
            p2 = xp_get_p(xp)
            e.w = int(p1 == p2)

        def f(e, a, b):
            i = 1024
            while i > 0:
                i >>= 1
                #
                xp = e.xp
                s = lltype.malloc(S)
                s.a = a
                s.b = b            
                xp_set_p(xp, s)

                x = xp_get_x(xp)
                newx = 2*x
                xp_set_x(xp, newx)
                g(e)            
                res = xp.x
                #
                myjitdriver.jit_merge_point(e=e, a=a, b=b, res=res, i=i)
                myjitdriver.can_enter_jit(e=e, a=a, b=b, res=res, i=i)
            return res

        def main(a, b, x):
            xp = lltype.malloc(XP)
            xp.vable_access = lltype.nullptr(XP_ACCESS)
            xp.x = x
            xp.p = lltype.nullptr(S)
            e = lltype.malloc(E2)
            e.xp = xp
            f(e, a, b)
            return e.w

        res = self.run(main, [2, 20, 10], threshold=2,
                       policy=StopAtXPolicy(g))
        assert res == main(2, 20, 10)

        res = self.run(main, [2, 20, 10], threshold=1,
                       policy=StopAtXPolicy(g))
        assert res == main(2, 20, 10)

    def test_force_unaliased_residual_red_call(self):
        myjitdriver = JitDriver(greens = [],
                                reds = ['e', 'a', 'b', 'i', 'res'])

        def g(e):
            pq = e.pq
            p = pq_get_p(pq)
            q = pq_get_q(pq)
            e.w = int(p != q)

        def f(e, a, b):
            i = 1024
            while i > 0:
                i >>= 1
                #
                pq = e.pq
                s = lltype.malloc(S)
                s.a = a
                s.b = b
                pq_set_p(pq, s)
                s = lltype.malloc(S)
                s.a = a
                s.b = b            
                pq_set_q(pq, s)
                g(e)            
                res = pq.p.a
                #
                myjitdriver.jit_merge_point(e=e, a=a, b=b, res=res, i=i)
                myjitdriver.can_enter_jit(e=e, a=a, b=b, res=res, i=i)
            return res

        def main(a, b, x):
            pq = lltype.malloc(PQ)
            pq.vable_access = lltype.nullptr(PQ_ACCESS)
            pq.p = lltype.nullptr(S)
            pq.q = pq.p
            e = lltype.malloc(E3)
            e.pq = pq
            f(e, a, b)
            return e.w

        res = self.run(main, [2, 20, 10], threshold=2,
                       policy=StopAtXPolicy(g))
        assert res == main(2, 20, 10)

        res = self.run(main, [2, 20, 10], threshold=1,
                       policy=StopAtXPolicy(g))
        assert res == main(2, 20, 10)

    def test_force_aliased_residual_red_call(self):
        myjitdriver = JitDriver(greens = [],
                                reds = ['e', 'a', 'b', 'i', 'res'])

        def g(e):
            pq = e.pq
            p = pq_get_p(pq)
            q = pq_get_q(pq)
            e.w = int(p == q)

        def f(e, a, b):
            i = 1024
            while i > 0:
                i >>= 1
                #
                pq = e.pq
                s = lltype.malloc(S)
                s.a = a
                s.b = b
                pq_set_p(pq, s)
                pq_set_q(pq, s)
                g(e)            
                res = pq.p.a
                #
                myjitdriver.jit_merge_point(e=e, a=a, b=b, res=res, i=i)
                myjitdriver.can_enter_jit(e=e, a=a, b=b, res=res, i=i)
            return res

        def main(a, b, x):
            pq = lltype.malloc(PQ)
            pq.vable_access = lltype.nullptr(PQ_ACCESS)
            pq.p = lltype.nullptr(S)
            pq.q = pq.p
            e = lltype.malloc(E3)
            e.pq = pq
            f(e, a, b)
            return e.w

        res = self.run(main, [2, 20, 10], threshold=2,
                       policy=StopAtXPolicy(g))
        assert res == main(2, 20, 10)

        res = self.run(main, [2, 20, 10], threshold=1,
                       policy=StopAtXPolicy(g))
        assert res == main(2, 20, 10)

    def test_force_in_residual_red_call_with_more_use(self):
        myjitdriver = JitDriver(greens = [],
                                reds = ['e', 'a', 'b', 'i', 'res'])

        def g(e):
            xp = e.xp
            p = xp_get_p(xp)
            x = xp_get_x(xp)
            e.w = p.a + p.b + x
            p.b, p.a = p.a, p.b

        def f(e, a, b):
            i = 1024
            while i > 0:
                i >>= 1
                #
                xp = e.xp
                s = lltype.malloc(S)
                s.a = a
                s.b = b
                xp_set_p(xp, s)

                x = xp_get_x(xp)
                newx = 2*x
                xp_set_x(xp, newx)
                g(e)
                s.a = s.a*7
                s.b = s.b*5
                res = xp.x
                #
                myjitdriver.jit_merge_point(e=e, a=a, b=b, res=res, i=i)
                myjitdriver.can_enter_jit(e=e, a=a, b=b, res=res, i=i)
            return res

        def main(a, b, x):
            xp = lltype.malloc(XP)
            xp.vable_access = lltype.nullptr(XP_ACCESS)
            xp.x = x
            xp.p = lltype.nullptr(S)
            e = lltype.malloc(E2)
            e.xp = xp
            f(e, a, b)
            return e.w + xp.p.a + xp.p.b

        res = self.run(main, [2, 20, 10], threshold=2,
                       policy=StopAtXPolicy(g))
        assert res == main(2, 20, 10)

        res = self.run(main, [2, 20, 10], threshold=1,
                       policy=StopAtXPolicy(g))
        assert res == main(2, 20, 10)

    def test_virtualizable_escaped_as_argument_to_red_call(self):
        myjitdriver = JitDriver(greens = [],
                                reds = ['x', 'y', 'i', 'res'])

        def g(xy):
            x = xy_get_x(xy)
            y = xy_get_y(xy)
            return y*2 + x

        def f(x, y):
            i = 1024
            while i > 0:
                i >>= 1
                #
                xy = lltype.malloc(XY)
                xy.vable_access = lltype.nullptr(XY_ACCESS)
                xy.x = x
                xy.y = y
                res = g(xy)
                x = xy_get_x(xy)
                y = xy_get_y(xy)
                #
                myjitdriver.jit_merge_point(x=x, y=y, res=res, i=i)
                myjitdriver.can_enter_jit(x=x, y=y, res=res, i=i)
            return res

        def main(x, y):
            return f(x,y)
        
        res = self.run(main, [20, 11], threshold=2,
                       policy=StopAtXPolicy(g))
        assert res == main(20, 11)

        res = self.run(main, [20, 11], threshold=1,
                       policy=StopAtXPolicy(g))
        assert res == main(20, 11)

    def test_setting_in_residual_call(self):
        myjitdriver = JitDriver(greens = [],
                                reds = ['x', 'i', 'res'])

        def g(xy):
            x = xy_get_x(xy)
            y = xy_get_y(xy)
            xy_set_x(xy, y)
            xy_set_y(xy, x)

        def f(x):
            i = 1024
            while i > 0:
                i >>= 1
                #
                xy = lltype.malloc(XY)
                xy.vable_access = lltype.nullptr(XY_ACCESS)
                xy.x = x
                xy.y = 11
                g(xy)
                x = xy_get_x(xy)
                y = xy_get_y(xy)
                res = x*2 + y
                #
                myjitdriver.jit_merge_point(x=x, res=res, i=i)
                myjitdriver.can_enter_jit(x=x, res=res, i=i)
            return res

        def main(x):
            return f(x)
        
        res = self.run(main, [20], threshold=2,
                       policy=StopAtXPolicy(g))
        assert res == main(20)

        res = self.run(main, [20], threshold=1,
                       policy=StopAtXPolicy(g))
        assert res == main(20)

class TestVirtualizableImplicit(test_hotpath.HotPathTest):
    type_system = "lltype"
    simplify_virtualizable_accesses = True

    def timeshift_from_portal(self, *args, **kwargs):
        py.test.skip("port me")

    def test_simple(self):
        myjitdriver = JitDriver(greens = [],
                                reds = ['xy', 'i', 'res'])

        class XY(object):
            _virtualizable_ = True
            
            def __init__(self, x, y):
                self.x = x
                self.y = y
   
        def f(xy):
            i = 1024
            while i > 0:
                i >>= 1
                res = xy.x+xy.y
                myjitdriver.jit_merge_point(xy=xy, res=res, i=i)
                myjitdriver.can_enter_jit(xy=xy, res=res, i=i)
            return res

        def main(x, y):
            xy = XY(x, y)
            return f(xy)

        res = self.run(main, [20, 22], threshold=2)
        assert res == 42
        self.check_insns_in_loops(getfield=0)

    def test_simple__class__(self):
        myjitdriver = JitDriver(greens = [],
                                reds = ['v', 'i', 'res'])

        class V(object):
            _virtualizable_ = True
            def __init__(self, a):
                self.a = a

        class V1(V):
            def __init__(self, b):
                V.__init__(self, 1)
                self.b = b

        class V2(V):
            def __init__(self):
                V.__init__(self, 2)

        def f(v):
            i = 1024
            while i > 0:
                i >>= 1
                res = v.__class__
                myjitdriver.jit_merge_point(v=v, res=res, i=i)
                myjitdriver.can_enter_jit(v=v, res=res, i=i)
            return res

        def main(x, y):
            if x:
                v = V1(42)
            else:
                v = V2()
            if y:
                c = None
            else:
                c = f(v)
            V2()
            return (c is not None) * 2 + (c is V1)

        res = self.run(main, [0, 1], threshold=2)
        assert res == 0
        self.check_nothing_compiled_at_all()
        res = self.run(main, [1, 0], threshold=2)
        assert res == 3
        self.check_insns_in_loops({'getfield': 1,
                                   'int_gt': 1, 'int_rshift': 1})
        res = self.run(main, [1, 0], threshold=1)
        assert res == 3
        res = self.run(main, [0, 0], threshold=2)
        assert res == 2
        res = self.run(main, [0, 0], threshold=1)
        assert res == 2

    def test_simple_inheritance(self):
        myjitdriver = JitDriver(greens = [],
                                reds = ['xy', 'i', 'res'])

        class X(object):
            _virtualizable_ = True
            
            def __init__(self, x):
                self.x = x

        class XY(X):

            def __init__(self, x, y):
                X.__init__(self, x)
                self.y = y
   
        def f(xy):
            i = 1024
            while i > 0:
                i >>= 1
                res = xy.x+xy.y
                myjitdriver.jit_merge_point(xy=xy, res=res, i=i)
                myjitdriver.can_enter_jit(xy=xy, res=res, i=i)
            return res

        def main(x, y):
            X(0)
            xy = XY(x, y)
            return f(xy)

        res = self.run(main, [20, 22], threshold=2)
        assert res == 42
        self.check_insns_in_loops(getfield=0)

        res = self.run(main, [20, 22], threshold=1)
        assert res == 42
        self.check_insns_in_loops(getfield=0)

    def test_simple_interpreter_with_frame(self):
        myjitdriver = JitDriver(greens = ['pc', 'n', 's'],
                                reds = ['frame'])

        class Log:
            acc = 0
        log = Log()
        class Frame(object):
            _virtualizable_ = True
            def __init__(self, code, acc, y):
                self.code = code
                self.pc = 0
                self.acc = acc
                self.y = y

            def run(self):
                self.plus_minus(self.code)
                assert self.pc == len(self.code)
                return self.acc

            def plus_minus(self, s):
                n = len(s)
                pc = 0
                while True:
                    myjitdriver.jit_merge_point(frame=self, pc=pc, n=n, s=s)
                    self.pc = pc
                    if hint(pc >= n, concrete=True):
                        break
                    op = s[pc]
                    op = hint(op, concrete=True)
                    pc += 1
                    if op == '+':
                        self.acc += self.y
                    elif op == '-':
                        self.acc -= self.y
                    elif op == 'r':
                        if self.acc > 0:
                            pc -= 3
                            assert pc >= 0
                            myjitdriver.can_enter_jit(frame=self, pc=pc,
                                                      n=n, s=s)
                    elif op == 'd':
                        self.debug()
                return 0

            def debug(self):
                log.acc = self.acc
            
        def main(x, y, case):
            code = ['+d+-+++++ -r++', '+++++++++d-r+++'][case]
            f = Frame(code, x, y)
            return f.run() * 10 + log.acc

        assert main(0, 2, 0) == 42
        assert main(0, 2, 1) == 62

        res = self.run(main, [0, 2, 0], threshold=2,
                       policy=StopAtXPolicy(Frame.debug.im_func))
        assert res == 42
        self.check_insns_in_loops({'int_sub': 1, 'int_gt': 1})

        res = self.run(main, [0, 2, 1], threshold=2,
                       policy=StopAtXPolicy(Frame.debug.im_func))
        assert res == 62


    def test_setting_pointer_in_residual_call(self):
        class S(object):
            def __init__(self, x, y):
                self.x = x
                self.y = y
            
        class V(object):
            _virtualizable_ = True
            def __init__(self, s):
                self.s = s

        def g(v):
            assert v.s is None
            s = S(1, 7)
            v.s = s
            
        def f(v):
            hint(None, global_merge_point=True)
            g(v)
            s = v.s
            return s.x + s.y

        def main():
            S(5, 5)
            v = V(None)
            return f(v)

        res = self.timeshift_from_portal(main, f, [], policy=StopAtXPolicy(g))
        assert res == 8

        
    def test_aliased_box(self):
        class S(object):
            def __init__(self, x):
                self.x = x

        class V(object):
            _virtualizable_ = True
            def __init__(self, x):
                self.x = x

        def g(v):
            v.x = 42
        
        def f(x):
            hint(None, global_merge_point=True)
            s = S(x)
            v = V(x)
            g(v)
            return v.x + s.x
        
        def main(x):
            s = S(19)
            r = f(x)
            return r
        
        res = self.timeshift_from_portal(main, f, [0], policy=StopAtXPolicy(g))
        assert res == 42

    def test_force_then_set_in_residual_call(self):
        class S(object):
            def __init__(self, x, y):
                self.x = x
                self.y = y
            
        class V(object):
            _virtualizable_ = True
            def __init__(self, s):
                self.s = s

        def g(v):
            s = v.s
            x = s.x
            y = s.y
            s.x = y
            s.y = x
            v.s = S(x*100, y*100)
            
        def f(v):
            hint(None, global_merge_point=True)
            s = S(1, 10)
            v.s = s
            g(v)
            s2 = v.s
            return s.x*2 + s.y + s2.x * 2 + s2.y

        def main():
            v = V(None)
            return f(v)

        res = self.timeshift_from_portal(main, f, [], policy=StopAtXPolicy(g))
        assert res == 20 + 1 + 200 + 1000


    def test_inheritance_with_residual_call(self):
        class S(object):
            def __init__(self, x, y):
                self.sx = x
                self.sy = y
            

        class X(object):
            _virtualizable_ = True
            
            def __init__(self, x):
                self.x = x

        class XY(X):

            def __init__(self, x, y, s):
                X.__init__(self, x)
                self.s = s
                self.y = y

        def g(xy):
            s = xy.s
            x = xy.x
            y = xy.y
            if x:
                xy.x = s.sx
                xy.y = s.sy
            if y:
                xy.s = S(x, y)
   
        def f(xy, sx, sy):
            hint(None, global_merge_point=True)
            xy.s = S(sx, sy)
            g(xy)
            return xy.x + xy.y * 16 + xy.s.sx * 16 ** 2 + xy.s.sy * 16 ** 3

        def main(x, y, sx, sy):
            X(0)
            xy = XY(x, y, None)
            return f(xy, sx, sy)

        res = self.timeshift_from_portal(main, f, [1, 2, 4, 8],
                                         policy=StopAtXPolicy(g))
        assert res == 4 + 8 * 16 + 1 * 16 ** 2 + 2 * 16 ** 3


    def test_force_then_set_in_residual_call_more(self):
        class S(object):
            def __init__(self, x, y):
                self.x = x
                self.y = y

        class T(object):
            def __init__(self, s1, s2):
                self.s1 = s1
                self.s2 = s2

        class V(object):
            _virtualizable_ = True
            def __init__(self, s, t):
                self.s = s
                self.t = t

        def g(v):
            s1 = v.s
            x = s1.x
            y = s1.y
            s1.x = y
            s1.y = x
            v.s = S(x*100, y*100)
            t = v.t
            s1bis = t.s1
            assert s1bis is s1
            s2 = t.s2
            x = s2.x
            y = s2.y
            s2.x = 5*y
            s2.y = 5*x
            t.s1 = s2
            
        def f(v):
            hint(None, global_merge_point=True)
            s1 = S(1, 10)
            s2 = S(3, 23)
            v.s = s1
            v.t = t0 = T(s1, s2)
            g(v)
            t = v.t
            assert t is t0
            assert t.s1 is t.s2
            assert t.s1 is s2
            assert v.s is not s1
            s3 = v.s
            return s1.x + 7*s1.y + s2.x + 11*s2.y + s3.x + 17 * s3.y 

        def main():
            v = V(None, None)
            return f(v)

        res = self.timeshift_from_portal(main, f, [], policy=StopAtXPolicy(g))
        assert res == main()



    def test_force_then_set_in_residual_call_evenmore(self):
        class S(object):
            def __init__(self, x, y):
                self.x = x
                self.y = y

        class T(object):
            def __init__(self, s1, s2):
                self.s1 = s1
                self.s2 = s2

        class V(object):
            _virtualizable_ = True
            def __init__(self, s, t):
                self.s = s
                self.t = t

        def g(v):
            s1 = v.s
            x = s1.x
            y = s1.y
            s1.x = y
            s1.y = x
            t = v.t
            s1bis = t.s1
            assert s1bis is s1
            s2 = t.s2
            x = s2.x
            y = s2.y
            s2.x = 5*y
            s2.y = 5*x
            t.s1 = s2
            v.t = T(t.s1, t.s2)
            
        def f(v):
            hint(None, global_merge_point=True)
            s1 = S(1, 10)
            s2 = S(3, 23)
            v.s = s1
            v.t = t0 = T(s1, s2)
            g(v)
            t = v.t

            assert t is not t0
            assert t.s1 is t.s2
            assert t.s1 is s2
            assert v.s is s1
            s3 = v.s
            return s1.x + 7*s1.y + s2.x + 11*s2.y + s3.x + 17 * s3.y 

        def main():
            v = V(None, None)
            return f(v)

        res = self.timeshift_from_portal(main, f, [], policy=StopAtXPolicy(g))
        assert res == main()


        
    def test_virtual_list(self):
        myjitdriver = JitDriver(greens = [],
                                reds = ['v', 'i', 'res'])

        class V(object):
            _virtualizable_ = True
            def __init__(self, l):
                self.l = l

        def g(v):
            l = v.l
            x = l[0]
            y = l[1]
            l[0] = y
            l[1] = x
            v.l = [x*100, y*100]
            
        def f(v):
            i = 1024
            while i > 0:
                i >>= 1
                l = [1, 10]
                v.l = l
                g(v)
                l2 = v.l
                res = l[0]*2 + l[1] + l2[0] * 2 + l2[1]
                myjitdriver.jit_merge_point(v=v, res=res, i=i)
                myjitdriver.can_enter_jit(v=v, res=res, i=i)
            return res

        def main():
            v = V(None)
            return f(v)

        res = self.run(main, [], threshold=2, policy=StopAtXPolicy(g))
        assert res == main()
        res = self.run(main, [], threshold=1, policy=StopAtXPolicy(g))
        assert res == main()

    def test_virtual_list_and_struct(self):
        myjitdriver = JitDriver(greens = [],
                                reds = ['v', 'i', 'res'])

        class S(object):
            def __init__(self, x, y):
                self.x = x
                self.y = y

        class V(object):
            _virtualizable_ = True
            def __init__(self, l, s):
                self.l = l
                self.s = s
        def g(v):
            l = v.l
            x = l[0]
            y = l[1]
            l[0] = y
            l[1] = x
            v.l = [x*100, y*100]
            
        def f(v):
            i = 1024
            while i > 0:
                i >>= 1
                l = [1, 10]
                s = S(3, 7)
                v.l = l
                v.s = s
                g(v)
                l2 = v.l
                s2 = v.s
                res = l[0]*2 + l[1] + l2[0] * 2 + l2[1] + s.x * 7 + s.y + s2.x * 7 + s2.y
                myjitdriver.jit_merge_point(v=v, res=res, i=i)
                myjitdriver.can_enter_jit(v=v, res=res, i=i)
            return res

        def main():
            v = V(None, None)
            return f(v)

        res = self.run(main, [], threshold=2, policy=StopAtXPolicy(g))
        assert res == main()
        res = self.run(main, [], threshold=1, policy=StopAtXPolicy(g))
        assert res == main()

    def test_simple_interpreter_with_frame_with_stack(self):
        class MyJitdriver(JitDriver):
            greens = ['pc', 's']
            reds = ['frame']

            def compute_invariants(self, reds, pc, s):
                frame = reds.frame
                stacklen = len(frame.stack)
                return stacklen

            def on_enter_jit(self, invariant, reds, pc, s):
                frame = reds.frame
                origstack = frame.stack
                stacklen = invariant
                curstack = []
                i = 0
                while i < stacklen:
                    hint(i, concrete=True)
                    curstack.append(origstack[i])
                    i += 1
                frame.stack = curstack
                log.expected_stack = None

        myjitdriver = MyJitdriver()

        class Log:
            stack = None
        log = Log()
        class Frame(object):
            _virtualizable_ = True
            def __init__(self, code, *args):
                self.code = code
                self.pc = 0
                self.stack = list(args)
                
            def run(self):
                self.trace = 0
                log.expected_stack = self.stack
                self.interpret(self.code)
                assert self.pc == len(self.code)
                assert len(self.stack) == 1
                return self.stack.pop()

            def interpret(self, s):
                pc = 0
                while True:
                    myjitdriver.jit_merge_point(frame=self, s=s, pc=pc)
                    self.pc = pc
                    if hint(pc >= len(s), concrete=True):
                        break
                    op = s[pc]
                    pc += 1
                    op = hint(op, concrete=True)
                    if op == 'P': 
                        arg = s[pc]
                        pc += 1
                        hint(arg, concrete=True)
                        self.stack.append(ord(arg) - ord('0')) 
                    elif op == 'D':
                        self.stack.append(self.stack[-1])    # dup
                    elif op == 'p':
                        self.stack.pop()
                    elif op == '+':
                        arg = self.stack.pop()
                        self.stack[-1] += arg
                    elif op == '-':
                        arg = self.stack.pop()
                        self.stack[-1] -= arg
                    elif op == 'J':
                        target = self.stack.pop()
                        cond = self.stack.pop()
                        if cond > 0:
                            pc = hint(target, promote=True)
                            myjitdriver.can_enter_jit(frame=self, s=s, pc=pc)
                    elif op == 't':
                        self.trace = self.trace * 3 + self.stack[-1]
                    elif op == 'd':
                        self.debug()
                    else:
                        raise NotImplementedError

            def debug(self):
                if log.expected_stack is not None:
                    assert self.stack is log.expected_stack
                log.expected_stack = self.stack
                for item in self.stack:
                    self.trace = self.trace * 7 - item
            
        def main(x, case, expected):
            code = ['P2+tP5+tP3-', 'P1+tP3-DP3J', 'P4d-DtP0J'][case]
            f = Frame(code, x)
            res = f.run()
            assert res == expected
            return f.trace

        assert main(38, 0, 42) == 40*3+45
        assert main(15, 1, -2) == ((((16*3+13)*3+10)*3+7)*3+4)*3+1
        main(41, 2, -3)   # to check that this works too

        if not self.translate_support_code:
            # one case is enough if translating the support code
            res = self.run(main, [38, 0, 42], threshold=2,
                           policy=StopAtXPolicy(Frame.debug.im_func))
            assert res == 40*3+45
            self.check_nothing_compiled_at_all()

            res = self.run(main, [15, 1, -2], threshold=2,
                           policy=StopAtXPolicy(Frame.debug.im_func))
            assert res == ((((16*3+13)*3+10)*3+7)*3+4)*3+1
            self.check_insns_in_loops({'int_sub': 1, 'int_gt': 1,
                                       'int_mul': 1, 'int_add': 1})

        res = self.run(main, [41, 2, -3], threshold=2,
                       policy=StopAtXPolicy(Frame.debug.im_func))
        assert intmask(res) == intmask(main(41, 2, -3))


    def test_virtual_list_and_struct_fallback(self):
        myjitdriver = JitDriver(greens = [],
                                reds = ['v', 'i', 'res'])

        class Counter:
            pass
        glob = Counter()

        def residual(idx, see):
            print 'RESIDUAL:', idx, see
            glob.counter[idx] += 1
            assert see == glob.counter[idx]

        class S(object):
            def __init__(self, x, y):
                self.x = x
                self.y = y

        class V(object):
            _virtualizable_ = True
            def summary(self):
                result = 0
                i = 0
                while i < len(self.l):
                    s = self.l[i]
                    result = (result * 100) + s.x * 10 + s.y
                    i += 1
                return result

        def f(v):
            i = 10
            while i > 0:
                i -= 1
                l = v.l = []
                l.append(S(6, 3))
                l.append(S(2, 7))
                residual(1, 10 - i)
                res = v.summary()
                l.pop()
                l.pop()
                assert len(l) == 0
                v.l = None
                myjitdriver.jit_merge_point(v=v, res=res, i=i)
                myjitdriver.can_enter_jit(v=v, res=res, i=i)
            return res

        def main():
            v = V()
            glob.counter = [0, 0, 0]
            res = f(v)
            assert glob.counter == [0, 10, 0]
            return res

        print main()

        res = self.run(main, [], threshold=2, policy=StopAtXPolicy(residual))
        assert res == main()
        self.check_insns_in_loops(malloc=0, direct_call=1)


    def test_recursive(self):

        class XY(object):
            _virtualizable_ = True
            
            def __init__(self, x, back):
                self.x = x
                self.back = back
   
        def f(xy):
            return xy.x

        def main(x, y):
            xyy = XY(y, None)
            xy = XY(x, xyy)
            return f(xy)

        res = self.timeshift_from_portal(main, f, [20, 22], policy=P_OOPSPEC)
        assert res == 20
        self.check_insns(getfield=0)


    def test_recursive_load_from(self):

        class W(object):
            def __init__(self, xy):
                self.xy = xy

        class XY(object):
            _virtualizable_ = True
            
            def __init__(self, x, back):
                self.x = x
                self.back = back
   
        def f(w):
            xy = w.xy
            return xy.x

        def main(x, y):
            xyy = XY(y, None)
            xy = XY(x, xyy)
            return f(W(xy))

        res = self.timeshift_from_portal(main, f, [20, 22], policy=P_OOPSPEC)
        assert res == 20

    def test_string_in_virtualizable(self):
        class S(object):
            def __init__(self, s):
                self.s = s

        class XY(object):
            _virtualizable_ = True
            
            def __init__(self, x, s):
                self.x = x
                self.s = s
        def g(xy):
            xy.x = 19 + len(xy.s.s)
   
        def f(x, n):
            hint(None, global_merge_point=True)
            s = S('2'*n)
            xy = XY(x, s)
            g(xy)
            return xy.s

        def main(x, y):
            return int(f(x, y).s)

        res = self.timeshift_from_portal(main, f, [20, 3],
                                         policy=StopAtXPolicy(g))
        assert res == 222

    def test_type_bug(self):
        myjitdriver = JitDriver(greens = [],
                                reds = ['x', 'v', 'i', 'res'])

        class V(object):
            _virtualizable_ = True

            def __init__(self, v):
                self.v = v

        def f(x, v):
            i = 1024
            while i > 0:
                i >>= 1
                #
                if x:
                    v.v = 0
                else:
                    pass
                res = x*2, v
                #
                myjitdriver.jit_merge_point(x=x, v=v, res=res, i=i)
                myjitdriver.can_enter_jit(x=x, v=v, res=res, i=i)
            return res

        def main(x,y):
            v = V(y)
            r, v1 = f(x, v)
            assert v1 is v
            assert type(v) is V
            assert v.v == 0
            return r

        assert main(20, 3) == 40
        res = self.run(main, [20, 3], threshold=2)
        assert res == 40

    def test_indirect_residual_call(self):
        class V(object):
            _virtualizable_ = True

            def __init__(self, v):
                self.v = v

        def g(v, n):
            v.v.append(n)      # force the virtualizable arg here
        def h1(v, n):
            g(v, n)
            return n * 6
        def h2(v, n):
            return n * 8

        l = [h2, h1]

        def f(n):
            hint(None, global_merge_point=True)
            v = V([100])
            h = l[n & 1]
            n += 10
            res = h(v, n)
            return res - v.v.pop()

        P = StopAtXPolicy(g)

        assert f(-3) == 35
        res = self.timeshift_from_portal(f, f, [-3], policy=P)
        assert res == 35
        res = self.timeshift_from_portal(f, f, [4], policy=P)
        assert res == 12
