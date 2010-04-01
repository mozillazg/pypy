
from pypy.module.cpyext.test.test_api import BaseApiTest

class TestEval(BaseApiTest):
    def test_eval(self, space, api):
        w_l, w_f = space.fixedview(space.appexec([], """():
        l = []
        def f(arg1, arg2):
            l.append(arg1)
            l.append(arg2)
            return len(l)
        return l, f
        """))

        w_t = space.newtuple([space.wrap(1), space.wrap(2)])
        w_res = api.PyEval_CallObjectWithKeywords(w_f, w_t, None)
        assert space.int_w(w_res) == 2
        assert space.int_w(space.len(w_l)) == 2
        w_f = space.appexec([], """():
            def f(*args, **kwds):
                assert isinstance(kwds, dict)
                assert 'xyz' in kwds
                return len(kwds) + len(args) * 10
            return f
            """)
        w_t = space.newtuple([space.w_None, space.w_None])
        w_d = space.newdict()
        space.setitem(w_d, space.wrap("xyz"), space.wrap(3))
        w_res = api.PyEval_CallObjectWithKeywords(w_f, w_t, w_d)
        assert space.int_w(w_res) == 21
