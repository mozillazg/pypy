
def test_register():
    from pypy.translator import register
    #
    from pypy.jit.backend.detect_cpu import autodetect
    if autodetect() == 'x86_64':
        assert register.eci is not None
        assert register.var_name_in_c is not None
        assert register.register_number == 15        # r15
    else:
        assert register.eci is None
        assert register.var_name_in_c is None
        assert register.register_number is None
