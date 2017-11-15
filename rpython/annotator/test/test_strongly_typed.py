
import py

from rpython.conftest import option

from rpython.annotator import model
from rpython.annotator.annrpython import RPythonAnnotator as _RPythonAnnotator


class TestAnnotateTestCase:
    class RPythonAnnotator(_RPythonAnnotator):
        def build_types(self, *args):
            s = _RPythonAnnotator.build_types(self, *args)
            self.validate()
            if option.view:
                self.translator.view()
            return s

    def build_types(self, func, types):
        a = self.RPythonAnnotator()
        return a.build_types(func, types)

    def test_simple(self):
        def f(a):
            return a

        s = model.SomeInteger()
        s.can_union = False
        self.build_types(f, [s])
        assert s == model.SomeInteger()

    def test_generalize_boom(self):
        def f(i):
            if i % 15 == 0:
                return f(1.5)
            return i

        s = model.SomeInteger()
        s.can_union = False
        py.test.raises(model.AnnotatorError, self.build_types, f, [s])
