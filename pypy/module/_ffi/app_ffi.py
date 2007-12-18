# NOT_RPYTHON


class Array(object):
    def __init__(self, of):
        import _ffi
        self.of = of
        _ffi._get_type(of)

    def __call__(self, size):
        from _ffi import ArrayInstance
        return ArrayInstance(self.of, size)
