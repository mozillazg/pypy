import py
from pypy.interpreter.argument import Arguments, ArgumentsForTranslation, ArgErr
from pypy.interpreter.argument import ArgErrUnknownKwds, rawshape
from pypy.interpreter.error import OperationError


class DummySpace(object):
    def newtuple(self, items):
        return tuple(items)

    def is_true(self, obj):
        return bool(obj)

    def viewiterable(self, it):
        return list(it)

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

    def len(self, x):
        return len(x)

    def int_w(self, x):
        return x

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
        args = Arguments(space, [])
        py.test.raises(ArgErr, args._match_signature, None, l, ["a"])
        args = Arguments(space, [])
        py.test.raises(ArgErr, args._match_signature, None, l, ["a"],
                       has_vararg=True)
        args = Arguments(space, [])
        l = [None]
        args._match_signature(None, l, ["a"], defaults_w=[1])
        assert l == [1]
        args = Arguments(space, [])
        l = [None]
        args._match_signature(None, l, [], has_vararg=True)
        assert l == [()]
        args = Arguments(space, [])
        l = [None]
        args._match_signature(None, l, [], has_kwarg=True)
        assert l == [{}]
        args = Arguments(space, [])
        l = [None, None]
        py.test.raises(ArgErr, args._match_signature, 41, l, [])
        args = Arguments(space, [])
        l = [None]
        args._match_signature(1, l, ["a"])
        assert l == [1]
        args = Arguments(space, [])
        l = [None]
        args._match_signature(1, l, [], has_vararg=True)
        assert l == [(1,)]

    def test_match4(self):
        space = DummySpace()
        values = [4, 5, 6, 7]
        for havefirstarg in [0, 1]:
            for i in range(len(values)-havefirstarg):
                arglist = values[havefirstarg:i+havefirstarg]
                starargs = tuple(values[i+havefirstarg:])
                if havefirstarg:
                    firstarg = values[0]
                else:
                    firstarg = None
                args = Arguments(space, arglist, w_stararg=starargs)
                l = [None, None, None, None]
                args._match_signature(firstarg, l, ["a", "b", "c", "d"])
                assert l == [4, 5, 6, 7]
                args = Arguments(space, arglist, w_stararg=starargs)
                l = [None, None, None, None, None, None]
                py.test.raises(ArgErr, args._match_signature, firstarg, l, ["a"])
                args = Arguments(space, arglist, w_stararg=starargs)
                l = [None, None, None, None, None, None]
                py.test.raises(ArgErr, args._match_signature, firstarg, l, ["a", "b", "c", "d", "e"])
                args = Arguments(space, arglist, w_stararg=starargs)
                l = [None, None, None, None, None, None]
                py.test.raises(ArgErr, args._match_signature, firstarg, l, ["a", "b", "c", "d", "e"],
                               has_vararg=True)
                l = [None, None, None, None, None]
                args = Arguments(space, arglist, w_stararg=starargs)
                args._match_signature(firstarg, l, ["a", "b", "c", "d", "e"], defaults_w=[1])
                assert l == [4, 5, 6, 7, 1]
                for j in range(len(values)):
                    l = [None] * (j + 1)
                    args = Arguments(space, arglist, w_stararg=starargs)
                    args._match_signature(firstarg, l, ["a", "b", "c", "d", "e"][:j], has_vararg=True)
                    assert l == values[:j] + [tuple(values[j:])]
                l = [None, None, None, None, None]
                args = Arguments(space, arglist, w_stararg=starargs)
                args._match_signature(firstarg, l, ["a", "b", "c", "d"], has_kwarg=True)
                assert l == [4, 5, 6, 7, {}]

    def test_match_kwds(self):
        space = DummySpace()
        for i in range(3):
            kwds = [("c", 3)]
            kwds_w = dict(kwds[:i])
            keywords = kwds_w.keys()
            keywords_w = kwds_w.values()
            w_kwds = dict(kwds[i:])
            if i == 2:
                w_kwds = None
            assert len(keywords) == len(keywords_w)
            args = Arguments(space, [1, 2], keywords[:], keywords_w[:], w_starstararg=w_kwds)
            l = [None, None, None]
            args._match_signature(None, l, ["a", "b", "c"], defaults_w=[4])
            assert l == [1, 2, 3]
            args = Arguments(space, [1, 2], keywords[:], keywords_w[:], w_starstararg=w_kwds)
            l = [None, None, None, None]
            args._match_signature(None, l, ["a", "b", "b1", "c"], defaults_w=[4, 5])
            assert l == [1, 2, 4, 3]
            args = Arguments(space, [1, 2], keywords[:], keywords_w[:], w_starstararg=w_kwds)
            l = [None, None, None, None]
            args._match_signature(None, l, ["a", "b", "c", "d"], defaults_w=[4, 5])
            assert l == [1, 2, 3, 5]
            args = Arguments(space, [1, 2], keywords[:], keywords_w[:], w_starstararg=w_kwds)
            l = [None, None, None, None]
            py.test.raises(ArgErr, args._match_signature, None, l,
                           ["c", "b", "a", "d"], defaults_w=[4, 5])
            args = Arguments(space, [1, 2], keywords[:], keywords_w[:], w_starstararg=w_kwds)
            l = [None, None, None, None]
            py.test.raises(ArgErr, args._match_signature, None, l,
                           ["a", "b", "c1", "d"], defaults_w=[4, 5])
            args = Arguments(space, [1, 2], keywords[:], keywords_w[:], w_starstararg=w_kwds)
            l = [None, None, None]
            args._match_signature(None, l, ["a", "b"], has_kwarg=True)
            assert l == [1, 2, {'c': 3}]

    def test_match_kwds2(self):
        space = DummySpace()
        kwds = [("c", 3), ('d', 4)]
        for i in range(4):
            kwds_w = dict(kwds[:i])
            keywords = kwds_w.keys()
            keywords_w = kwds_w.values()
            w_kwds = dict(kwds[i:])
            if i == 3:
                w_kwds = None
            args = Arguments(space, [1, 2], keywords, keywords_w, w_starstararg=w_kwds)
            l = [None, None, None, None]
            args._match_signature(None, l, ["a", "b", "c"], has_kwarg=True)
            assert l == [1, 2, 3, {'d': 4}]

    def test_duplicate_kwds(self):
        space = DummySpace()
        excinfo = py.test.raises(OperationError, Arguments, space, [], ["a"],
                                 [1], w_starstararg={"a": 2})
        assert excinfo.value.w_type is TypeError

    def test_starstararg_wrong_type(self):
        space = DummySpace()
        excinfo = py.test.raises(OperationError, Arguments, space, [], ["a"],
                                 [1], w_starstararg="hello")
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
        excinfo = py.test.raises(OperationError, Arguments, space, [],
                                 ["a"], [1], w_starstararg={None: 1})
        assert excinfo.value.w_type is TypeError
        assert excinfo.value.w_value is not None
        excinfo = py.test.raises(OperationError, Arguments, space, [],
                                 ["a"], [1], w_starstararg={valuedummy: 1})
        assert excinfo.value.w_type is ValueError
        assert excinfo.value.w_value is None


    def test_blindargs(self):
        space = DummySpace()
        kwds = [("a", 3), ('b', 4)]
        for i in range(4):
            kwds_w = dict(kwds[:i])
            keywords = kwds_w.keys()
            keywords_w = kwds_w.values()
            w_kwds = dict(kwds[i:])
            if i == 3:
                w_kwds = None
            args = Arguments(space, [1, 2], keywords[:], keywords_w[:],
                             w_starstararg=w_kwds)
            l = [None, None, None]
            args._match_signature(None, l, ["a", "b"], has_kwarg=True, blindargs=2)
            assert l == [1, 2, {'a':3, 'b': 4}]
            args = Arguments(space, [1, 2], keywords[:], keywords_w[:],
                             w_starstararg=w_kwds)
            l = [None, None, None]
            py.test.raises(ArgErrUnknownKwds, args._match_signature, None, l,
                           ["a", "b"], blindargs=2)


def make_arguments_for_translation(space, args_w, keywords_w={},
                                   w_stararg=None, w_starstararg=None):
    return ArgumentsForTranslation(space, args_w, keywords_w.keys(),
                                   keywords_w.values(), w_stararg,
                                   w_starstararg)

class TestArgumentsForTranslation(object):

    def test_unmatch_signature(self):
        space = DummySpace()
        args = make_arguments_for_translation(space, [1,2,3])
        sig = (['a', 'b', 'c'], None, None)
        data = args.match_signature(sig, [])
        new_args = args.unmatch_signature(sig, data)
        assert args.unpack() == new_args.unpack()

        args = make_arguments_for_translation(space, [1])
        sig = (['a', 'b', 'c'], None, None)
        data = args.match_signature(sig, [2, 3])
        new_args = args.unmatch_signature(sig, data)
        assert args.unpack() == new_args.unpack()

        args = make_arguments_for_translation(space, [1,2,3,4,5])
        sig = (['a', 'b', 'c'], 'r', None)
        data = args.match_signature(sig, [])
        new_args = args.unmatch_signature(sig, data)
        assert args.unpack() == new_args.unpack()

        args = make_arguments_for_translation(space, [1], {'c': 3, 'b': 2})
        sig = (['a', 'b', 'c'], None, None)
        data = args.match_signature(sig, [])
        new_args = args.unmatch_signature(sig, data)
        assert args.unpack() == new_args.unpack()

        args = make_arguments_for_translation(space, [1], {'c': 5})
        sig = (['a', 'b', 'c'], None, None)
        data = args.match_signature(sig, [2, 3])
        new_args = args.unmatch_signature(sig, data)
        assert args.unpack() == new_args.unpack()

        args = make_arguments_for_translation(space, [1], {'c': 5, 'd': 7})
        sig = (['a', 'b', 'c'], None, 'kw')
        data = args.match_signature(sig, [2, 3])
        new_args = args.unmatch_signature(sig, data)
        assert args.unpack() == new_args.unpack()

        args = make_arguments_for_translation(space, [1,2,3,4,5], {'e': 5, 'd': 7})
        sig = (['a', 'b', 'c'], 'r', 'kw')
        data = args.match_signature(sig, [2, 3])
        new_args = args.unmatch_signature(sig, data)
        assert args.unpack() == new_args.unpack()

        args = make_arguments_for_translation(space, [], {},
                                       w_stararg=[1],
                                       w_starstararg={'c': 5, 'd': 7})
        sig = (['a', 'b', 'c'], None, 'kw')
        data = args.match_signature(sig, [2, 3])
        new_args = args.unmatch_signature(sig, data)
        assert args.unpack() == new_args.unpack()

        args = make_arguments_for_translation(space, [1,2], {'g': 9},
                                       w_stararg=[3,4,5],
                                       w_starstararg={'e': 5, 'd': 7})
        sig = (['a', 'b', 'c'], 'r', 'kw')
        data = args.match_signature(sig, [2, 3])
        new_args = args.unmatch_signature(sig, data)
        assert args.unpack() == new_args.unpack()

    def test_rawshape(self):
        space = DummySpace()
        args = make_arguments_for_translation(space, [1,2,3])
        assert rawshape(args) == (3, (), False, False)

        args = make_arguments_for_translation(space, [1])
        assert rawshape(args, 2) == (3, (), False, False)

        args = make_arguments_for_translation(space, [1,2,3,4,5])
        assert rawshape(args) == (5, (), False, False)

        args = make_arguments_for_translation(space, [1], {'c': 3, 'b': 2})
        assert rawshape(args) == (1, ('b', 'c'), False, False)

        args = make_arguments_for_translation(space, [1], {'c': 5})
        assert rawshape(args) == (1, ('c', ), False, False)

        args = make_arguments_for_translation(space, [1], {'c': 5, 'd': 7})
        assert rawshape(args) == (1, ('c', 'd'), False, False)

        args = make_arguments_for_translation(space, [1,2,3,4,5], {'e': 5, 'd': 7})
        assert rawshape(args) == (5, ('d', 'e'), False, False)

        args = make_arguments_for_translation(space, [], {},
                                       w_stararg=[1],
                                       w_starstararg={'c': 5, 'd': 7})
        assert rawshape(args) == (0, (), True, True)

        args = make_arguments_for_translation(space, [1,2], {'g': 9},
                                       w_stararg=[3,4,5],
                                       w_starstararg={'e': 5, 'd': 7})
        assert rawshape(args) == (2, ('g', ), True, True)

    def test_flatten(self):
        space = DummySpace()
        args = make_arguments_for_translation(space, [1,2,3])
        assert args.flatten() == ((3, (), False, False), [1, 2, 3])

        args = make_arguments_for_translation(space, [1])
        assert args.flatten() == ((1, (), False, False), [1])

        args = make_arguments_for_translation(space, [1,2,3,4,5])
        assert args.flatten() == ((5, (), False, False), [1,2,3,4,5])

        args = make_arguments_for_translation(space, [1], {'c': 3, 'b': 2})
        assert args.flatten() == ((1, ('b', 'c'), False, False), [1, 2, 3])

        args = make_arguments_for_translation(space, [1], {'c': 5})
        assert args.flatten() == ((1, ('c', ), False, False), [1, 5])

        args = make_arguments_for_translation(space, [1], {'c': 5, 'd': 7})
        assert args.flatten() == ((1, ('c', 'd'), False, False), [1, 5, 7])

        args = make_arguments_for_translation(space, [1,2,3,4,5], {'e': 5, 'd': 7})
        assert args.flatten() == ((5, ('d', 'e'), False, False), [1, 2, 3, 4, 5, 7, 5])

        args = make_arguments_for_translation(space, [], {},
                                       w_stararg=[1],
                                       w_starstararg={'c': 5, 'd': 7})
        assert args.flatten() == ((0, (), True, True), [[1], {'c': 5, 'd': 7}])

        args = make_arguments_for_translation(space, [1,2], {'g': 9},
                                       w_stararg=[3,4,5],
                                       w_starstararg={'e': 5, 'd': 7})
        assert args.flatten() == ((2, ('g', ), True, True), [1, 2, 9, [3, 4, 5], {'e': 5, 'd': 7}])

    def test_stararg_flowspace_variable(self):
        space = DummySpace()
        var = object()
        shape = ((2, ('g', ), True, False), [1, 2, 9, var])
        args = make_arguments_for_translation(space, [1,2], {'g': 9},
                                       w_stararg=var)
        assert args.flatten() == shape

        args = ArgumentsForTranslation.fromshape(space, *shape)
        assert args.flatten() == shape


    def test_fromshape(self):
        space = DummySpace()
        shape = ((3, (), False, False), [1, 2, 3])
        args = ArgumentsForTranslation.fromshape(space, *shape)
        assert args.flatten() == shape

        shape = ((1, (), False, False), [1])
        args = ArgumentsForTranslation.fromshape(space, *shape)
        assert args.flatten() == shape

        shape = ((5, (), False, False), [1,2,3,4,5])
        args = ArgumentsForTranslation.fromshape(space, *shape)
        assert args.flatten() == shape

        shape = ((1, ('b', 'c'), False, False), [1, 2, 3])
        args = ArgumentsForTranslation.fromshape(space, *shape)
        assert args.flatten() == shape

        shape = ((1, ('c', ), False, False), [1, 5])
        args = ArgumentsForTranslation.fromshape(space, *shape)
        assert args.flatten() == shape

        shape = ((1, ('c', 'd'), False, False), [1, 5, 7])
        args = ArgumentsForTranslation.fromshape(space, *shape)
        assert args.flatten() == shape

        shape = ((5, ('d', 'e'), False, False), [1, 2, 3, 4, 5, 7, 5])
        args = ArgumentsForTranslation.fromshape(space, *shape)
        assert args.flatten() == shape

        shape = ((0, (), True, True), [[1], {'c': 5, 'd': 7}])
        args = ArgumentsForTranslation.fromshape(space, *shape)
        assert args.flatten() == shape

        shape = ((2, ('g', ), True, True), [1, 2, 9, [3, 4, 5], {'e': 5, 'd': 7}])
        args = ArgumentsForTranslation.fromshape(space, *shape)
        assert args.flatten() == shape
