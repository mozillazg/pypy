import py
from pypy.interpreter.argument import Arguments, ArgumentsForTranslation, ArgErr
from pypy.interpreter.argument import ArgErrUnknownKwds
from pypy.interpreter.error import OperationError


class DummySpace(object):
    def newtuple(self, items):
        return tuple(items)

    def is_true(self, obj):
        return bool(obj)

    def unpackiterable(self, it):
        return list(it)

    def newdict(self):
        return {}

    def setitem(self, obj, key, value):
        obj[key] = value

    def getitem(self, obj, key):
        return obj[key]

    def wrap(self, obj):
        return obj

    def str_w(self, s):
        return str(s)

    def isinstance(self, obj, cls):
        return isinstance(obj, cls)

    def exception_match(self, w_type1, w_type2):
        return issubclass(w_type1, w_type2)


    w_TypeError = TypeError
    w_dict = dict

class TestArgumentsNormal(object):
    def test_match0(self):
        space = DummySpace()
        args = Arguments(space, [])
        l = []
        args._match_signature(None, l, [])
        assert len(l) == 0
        l = [None, None]
        py.test.raises(ArgErr, args._match_signature, None, l, ["a"])
        py.test.raises(ArgErr, args._match_signature, None, l, ["a"],
                       has_vararg=True)
        l = [None]
        args._match_signature(None, l, ["a"], defaults_w=[1])
        assert l == [1]
        l = [None]
        args._match_signature(None, l, [], has_vararg=True)
        assert l == [()]
        l = [None]
        args._match_signature(None, l, [], has_kwarg=True)
        assert l == [{}]
        l = [None, None]
        py.test.raises(ArgErr, args._match_signature, 41, l, [])
        l = [None]
        args._match_signature(1, l, ["a"])
        assert l == [1]
        l = [None]
        args._match_signature(1, l, [], has_vararg=True)
        assert l == [(1,)]

    def test_match4(self):
        space = DummySpace()
        values = [4, 5, 6, 7]
        for havefirstarg in [0, 1]:
            for i in range(len(values)-havefirstarg):
                args = values[havefirstarg:i+havefirstarg]
                starargs = tuple(values[i+havefirstarg:])
                if havefirstarg:
                    firstarg = values[0]
                else:
                    firstarg = None
                args = Arguments(space, args, w_stararg=starargs)
                l = [None, None, None, None]
                args._match_signature(firstarg, l, ["a", "b", "c", "d"])
                assert l == [4, 5, 6, 7]
                l = [None, None, None, None, None, None]
                py.test.raises(ArgErr, args._match_signature, firstarg, l, ["a"])
                py.test.raises(ArgErr, args._match_signature, firstarg, l, ["a", "b", "c", "d", "e"])
                py.test.raises(ArgErr, args._match_signature, firstarg, l, ["a", "b", "c", "d", "e"],
                               has_vararg=True)
                l = [None, None, None, None, None]
                args._match_signature(firstarg, l, ["a", "b", "c", "d", "e"], defaults_w=[1])
                assert l == [4, 5, 6, 7, 1]
                for j in range(len(values)):
                    l = [None] * (j + 1)
                    args._match_signature(firstarg, l, ["a", "b", "c", "d", "e"][:j], has_vararg=True)
                    assert l == values[:j] + [tuple(values[j:])]
                l = [None, None, None, None, None]
                args._match_signature(firstarg, l, ["a", "b", "c", "d"], has_kwarg=True)
                assert l == [4, 5, 6, 7, {}]

    def test_match_kwds(self):
        space = DummySpace()
        for i in range(3):
            kwds = [("c", 3)]
            kwds_w = dict(kwds[:i])
            w_kwds = dict(kwds[i:])
            if i == 2:
                w_kwds = None
            args = Arguments(space, [1, 2], kwds_w, w_starstararg=w_kwds)
            l = [None, None, None]
            args._match_signature(None, l, ["a", "b", "c"], defaults_w=[4])
            assert l == [1, 2, 3]
            l = [None, None, None, None]
            args._match_signature(None, l, ["a", "b", "b1", "c"], defaults_w=[4, 5])
            assert l == [1, 2, 4, 3]
            l = [None, None, None, None]
            args._match_signature(None, l, ["a", "b", "c", "d"], defaults_w=[4, 5])
            assert l == [1, 2, 3, 5]
            l = [None, None, None, None]
            py.test.raises(ArgErr, args._match_signature, None, l,
                           ["c", "b", "a", "d"], defaults_w=[4, 5])
            py.test.raises(ArgErr, args._match_signature, None, l,
                           ["a", "b", "c1", "d"], defaults_w=[4, 5])
            l = [None, None, None]
            args._match_signature(None, l, ["a", "b"], has_kwarg=True)
            assert l == [1, 2, {'c': 3}]

    def test_match_kwds2(self):
        space = DummySpace()
        kwds = [("c", 3), ('d', 4)]
        for i in range(4):
            kwds_w = dict(kwds[:i])
            w_kwds = dict(kwds[i:])
            if i == 3:
                w_kwds = None
            args = Arguments(space, [1, 2], kwds_w, w_starstararg=w_kwds)
            l = [None, None, None, None]
            args._match_signature(None, l, ["a", "b", "c"], has_kwarg=True)
            assert l == [1, 2, 3, {'d': 4}]

    def test_duplicate_kwds(self):
        space = DummySpace()
        args = Arguments(space, [], {"a": 1}, w_starstararg={"a": 2})
        excinfo = py.test.raises(OperationError, args._match_signature, None,
                                 [None], [], has_kwarg=True)
        assert excinfo.value.w_type is TypeError

    def test_starstararg_wrong_type(self):
        space = DummySpace()
        args = Arguments(space, [], {"a": 1}, w_starstararg="hello")
        excinfo = py.test.raises(OperationError, args._match_signature, None,
                                 [None], [], has_kwarg=True)
        assert excinfo.value.w_type is TypeError

    def test_unwrap_error(self):
        space = DummySpace()
        valuedummy = object()
        def str_w(w):
            if w is None:
                raise OperationError(TypeError, None)
            if w is valuedummy:
                raise OperationError(ValueError, None)
            return str(w)
        space.str_w = str_w
        args = Arguments(space, [], {"a": 1}, w_starstararg={None: 1})
        excinfo = py.test.raises(OperationError, args._match_signature, None,
                                 [None], [], has_kwarg=True)
        assert excinfo.value.w_type is TypeError
        assert excinfo.value.w_value is not None
        args = Arguments(space, [], {"a": 1}, w_starstararg={valuedummy: 1})
        excinfo = py.test.raises(OperationError, args._match_signature, None,
                                 [None], [], has_kwarg=True)
        assert excinfo.value.w_type is ValueError
        assert excinfo.value.w_value is None


    def test_blindargs(self):
        space = DummySpace()
        kwds = [("a", 3), ('b', 4)]
        for i in range(4):
            kwds_w = dict(kwds[:i])
            w_kwds = dict(kwds[i:])
            if i == 3:
                w_kwds = None
            args = Arguments(space, [1, 2], kwds_w, w_starstararg=w_kwds)
            l = [None, None, None]
            args._match_signature(None, l, ["a", "b"], has_kwarg=True, blindargs=2)
            assert l == [1, 2, {'a':3, 'b': 4}]
            py.test.raises(ArgErrUnknownKwds, args._match_signature, None, l,
                           ["a", "b"], blindargs=2)



class TestArgumentsForTranslation(object):

    def test_unmatch_signature(self):
        space = DummySpace()
        args = ArgumentsForTranslation(space, [1,2,3])
        sig = (['a', 'b', 'c'], None, None)
        data = args.match_signature(sig, [])
        new_args = args.unmatch_signature(sig, data)
        assert args.unpack() == new_args.unpack()

        args = ArgumentsForTranslation(space, [1])
        sig = (['a', 'b', 'c'], None, None)
        data = args.match_signature(sig, [2, 3])
        new_args = args.unmatch_signature(sig, data)
        assert args.unpack() == new_args.unpack()

        args = ArgumentsForTranslation(space, [1,2,3,4,5])
        sig = (['a', 'b', 'c'], 'r', None)
        data = args.match_signature(sig, [])
        new_args = args.unmatch_signature(sig, data)
        assert args.unpack() == new_args.unpack()

        args = ArgumentsForTranslation(space, [1], {'c': 3, 'b': 2})
        sig = (['a', 'b', 'c'], None, None)
        data = args.match_signature(sig, [])
        new_args = args.unmatch_signature(sig, data)
        assert args.unpack() == new_args.unpack()

        args = ArgumentsForTranslation(space, [1], {'c': 5})
        sig = (['a', 'b', 'c'], None, None)
        data = args.match_signature(sig, [2, 3])
        new_args = args.unmatch_signature(sig, data)
        assert args.unpack() == new_args.unpack()

        args = ArgumentsForTranslation(space, [1], {'c': 5, 'd': 7})
        sig = (['a', 'b', 'c'], None, 'kw')
        data = args.match_signature(sig, [2, 3])
        new_args = args.unmatch_signature(sig, data)
        assert args.unpack() == new_args.unpack()

        args = ArgumentsForTranslation(space, [1,2,3,4,5], {'e': 5, 'd': 7})
        sig = (['a', 'b', 'c'], 'r', 'kw')
        data = args.match_signature(sig, [2, 3])
        new_args = args.unmatch_signature(sig, data)
        assert args.unpack() == new_args.unpack()

        args = ArgumentsForTranslation(space, [], {},
                                       w_stararg=[1],
                                       w_starstararg={'c': 5, 'd': 7})
        sig = (['a', 'b', 'c'], None, 'kw')
        data = args.match_signature(sig, [2, 3])
        new_args = args.unmatch_signature(sig, data)
        assert args.unpack() == new_args.unpack()

        args = ArgumentsForTranslation(space, [1,2], {'g': 9},
                                       w_stararg=[3,4,5],
                                       w_starstararg={'e': 5, 'd': 7})
        sig = (['a', 'b', 'c'], 'r', 'kw')
        data = args.match_signature(sig, [2, 3])
        new_args = args.unmatch_signature(sig, data)
        assert args.unpack() == new_args.unpack()

