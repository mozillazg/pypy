#noinspection PyUnresolvedReferences
class AppTestJvm(object):
    def setup_class(cls):
        from pypy.conftest import gettestobjspace

        space = gettestobjspace(usemodules=('jvm',))
        cls.space = space

    def test_new(self):
        import jvm

        POINT = 'java.awt.Point'
        p1 = jvm.new(POINT)
        p2 = jvm.new(POINT, (p1, POINT))
        assert p1 == p1
        assert p1 != p2

    def test_new_bad_class_name(self):
        import jvm

        try:
            jvm.new('foo')
        except TypeError:
            pass
        else:
            assert False

    def test_new_exception_in_constructor(self):
        import jvm

        try:
            jvm.new('java.lang.StringBuilder', (-1, int))
        except RuntimeError:
            pass
        else:
            assert False

    def test_new_bad_arg_type(self):
        import jvm

        try:
            POINT = 'java.awt.Point'
            p1 = jvm.new(POINT)
            jvm.new(POINT, (p1, 'foo'))
        except TypeError:
            pass
        else:
            assert False

    def test_bad_method_name(self):
        import jvm

        try:
            POINT = 'java.awt.Point'
            p1 = jvm.new(POINT)
            jvm.call_method(p1, 'foobar')
        except TypeError:
            pass
        else:
            assert False

    def test_bad_type_name(self):
        import jvm

        try:
            POINT = 'java.awt.Point'
            p1 = jvm.new(POINT)
            p2 = jvm.new(POINT, (p1, 'foo'))
            jvm.call_method(p1, 'equals', (p2, 'foobar'))
        except TypeError:
            pass
        else:
            assert False

    def test_exception_in_method(self):
        import jvm

        sb = jvm.new('java.lang.StringBuilder')
        try:
            jvm.call_method(sb, 'setLength', (-1, int))
        except RuntimeError:
            pass
        else:
            assert False

    def test_get_methods(self):
        import jvm

        ms = jvm.get_methods('java.lang.Object')
        assert isinstance(ms, dict)
        assert set(ms.keys()) == {'equals',
                                  'getClass',
                                  'hashCode',
                                  'notify',
                                  'notifyAll',
                                  'toString',
                                  'wait'}
        assert len(ms['wait']) == 3

        ms = jvm.get_methods('java.lang.StringBuilder')
        appends = ms['append']
        for ret_type, args in appends:
            assert 'Abstract' not in ret_type
            assert not ret_type.startswith('[')
            for a in args:
                assert not a.startswith('[')

    def test_call_method_equals(self):
        import jvm

        POINT = 'java.awt.Point'
        p1 = jvm.new(POINT)
        p2 = jvm.new(POINT, (p1, POINT))

        (res, tpe) = jvm.call_method(p1, 'equals', (p2, 'java.lang.Object'))
        assert isinstance(tpe, str)
        assert tpe == 'java.lang.Boolean'

    def test_call_method_toString(self):
        import jvm

        p1 = jvm.new('java.awt.Point')
        (res, tpe) = jvm.call_method(p1, 'toString')
        assert tpe == 'java.lang.String'

    def test_unboxing(self):
        import jvm

        p1 = jvm.new('java.awt.Point')
        s, _ = jvm.call_method(p1, 'toString')
        unboxed_str = jvm.unbox(s)
        assert isinstance(unboxed_str, str)
        assert unboxed_str == 'java.awt.Point[x=0,y=0]'

        l, _ = jvm.call_method(s, 'length')
        unboxed_int = jvm.unbox(l)
        assert isinstance(unboxed_int, int)
        assert unboxed_int == len('java.awt.Point[x=0,y=0]')

        b, _ = jvm.call_method(s, 'isEmpty')
        unboxed_bool = jvm.unbox(b)
        assert isinstance(unboxed_bool, bool)
        assert unboxed_bool == False

    def test_boxing(self):
        import jvm

        for obj in ['foobar', 1, 7.3, False]:
            boxed_obj = jvm.box(obj)
            assert '_JvmObject' in repr(boxed_obj)

        try:
            jvm.box(None)
        except TypeError:
            pass
        else:
            assert False

    def test_int_argument(self):
        import jvm

        jvm.new('java.util.ArrayList', (10, int))

    def test_void_method(self):
        import jvm

        al = jvm.new('java.util.ArrayList')
        (res, tpe) = jvm.call_method(al, 'clear')
        assert res is None
        assert tpe == 'void'

    def test_bool_argument(self):
        import jvm

        t = jvm.new('java.lang.Thread')
        jvm.call_method(t, 'setDaemon', (True, bool))
        (res, tpe) = jvm.call_method(t, 'isDaemon')
        assert tpe == 'java.lang.Boolean'
        assert jvm.unbox(res) is True

    def test_str_argument(self):
        import jvm

        sb = jvm.new('java.lang.StringBuilder', ('foobar', str))
        res, _ = jvm.call_method(sb, 'toString')
        assert jvm.unbox(res) == 'foobar'

    def test_superclass(self):
        import jvm

        assert jvm.superclass('java.lang.String') == 'java.lang.Object'
        assert jvm.superclass(
            'java.lang.StringBuilder') == 'java.lang.AbstractStringBuilder'
        assert jvm.superclass('java.lang.Object') is None

    def test_get_field(self):
        import jvm

        p1 = jvm.new('java.awt.Point')
        res, tpe = jvm.get_field_value(p1, 'x')
        assert res is not None
        assert tpe == 'java.lang.Integer'

    def test_get_bad_field(self):
        import jvm

        p1 = jvm.new('java.awt.Point')
        try:
            jvm.get_field_value(p1, 'foobar')
        except TypeError:
            pass
        else:
            assert False

    def test_get_fields(self):
        import jvm
        fs = jvm.get_fields('java.awt.Point')
        assert set(fs) == {'x', 'y'}

    def test_api_get_fields(self):
        from jvm import java
        p = java.awt.Point()
        assert 'x' in dir(p)
        assert p.x == 0
        p.setLocation(17, 42)
        assert p.x == 17

    def test_get_constructors(self):
        import jvm
        cs = jvm.get_constructors('java.lang.Object')
        assert cs == ((),)

        cs = jvm.get_constructors('java.awt.Point')
        assert set(cs) == {(), ('int', 'int'), ('java.awt.Point',)}

    def test_api_constructors(self):
        from jvm import java
        p1 = java.awt.Point()
        assert p1.x == 0
        p1.setLocation(17,42)
        assert p1.x == 17
        p2 = java.awt.Point(8,8)
        assert p2.x == 8
        p3 = java.awt.Point(p1)
        assert p3.x == 17

    def test_setting_fields(self):
        import jvm
        from jvm import java

        p = java.awt.Point()
        assert p.x == 0
        jvm.set_field_value(p._inst, 'x', 17)
        assert p.x == 17
        p.x = 42
        assert p.x == 42


    def test_overloading_exact_match(self):
        from jvm import java

        sb = java.lang.StringBuilder()
        assert 'append' in dir(sb)
        assert 'StringBuilder' in str(type(sb))
        sb.append(42)
        sb.append(True)
        sb.append('Foobar')
        assert sb.toString() == '42trueFoobar'

        al = java.util.ArrayList()
        assert al.size() == 0
        o = java.lang.Object()
        al.add(o)
        assert al.size() == 1

    def test_overloading_nonexact_match(self):
        from jvm import java

        al = java.util.ArrayList()
        al.add('foobar')
        assert al.size() == 1
        o = java.lang.Object()
        al.add(o)
        assert al.size() == 2

    def test_static_methods(self):
        import jvm
        ms = jvm.get_static_methods('java.util.Collections')
        assert isinstance(ms, dict)
        assert 'emptyList' in ms

        res, tpe = jvm.call_static_method('java.util.Collections', 'emptyList')
        assert res is not None
        assert 'list' in tpe.lower()

        res, tpe = jvm.call_static_method('java.lang.Math', 'abs', (-17, int))
        assert tpe == 'java.lang.Integer'
        assert jvm.unbox(res) == 17

    def test_api_static_methods(self):
        from jvm import java
        assert 'abs' in dir(java.lang.Math)
        assert java.lang.Math.abs(-17) == 17

    def test_static_fields(self):
        import jvm
        res, tpe = jvm.get_static_field_value('java.lang.Integer', 'SIZE')
        assert tpe == 'java.lang.Integer'
        assert jvm.unbox(res) == 32

        from jvm import java
        assert java.lang.Integer.SIZE == 32

    def test_floats(self):
        from jvm import java
        pi = java.lang.Math.PI
        assert 3 < pi < 4
        p = java.awt.Point()
        p.setLocation(7.0, 12.0)
        assert p.x == 7


if __name__ == '__main__':
    # You can run this file directly using the compiled pypy-jvm interpreter,
    # just in case.
    tests = AppTestJvm()

    print
    print '=' * 80
    print

    for test_name in [name for name in dir(tests) if name.startswith('test_')]:
        print test_name,
        test_case = getattr(tests, test_name)
        try:
            test_case()
        except Exception:
            print
            print 'FAIL!!!!!!'
            print
        else:
            print 'OK'

    print
