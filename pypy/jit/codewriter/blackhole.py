from pypy.rlib.unroll import unrolling_iterable
from pypy.tool.sourcetools import func_with_new_name


def arguments(*argtypes, **kwds):
    resulttype = kwds.pop('returns', None)
    assert not kwds
    def decorate(function):
        function.argtypes = argtypes
        function.resulttype = resulttype
        return function
    return decorate

class LeaveFrame(Exception):
    pass


class BlackholeInterpreter(object):

    def __init__(self):
        self.registers_i = [0] * 256

    def setup_insns(self, insns):
        assert len(insns) <= 256, "too many instructions!"
        self._insns = [None] * len(insns)
        for key, value in insns.items():
            assert self._insns[value] is None
            self._insns[value] = key
        #
        all_funcs = []
        for key in self._insns:
            assert key is not None, "hole!"
            assert key.count('/') == 1, "bad key: %r" % (key,)
            name, argcodes = key.split('/')
            all_funcs.append(self._get_method(name, argcodes))
        all_funcs = unrolling_iterable(enumerate(all_funcs))
        #
        def dispatch(code, position):
            opcode = ord(code[position])
            position += 1
            for i, func in all_funcs:
                if opcode == i:
                    return func(code, position)
            else:
                raise AssertionError("bad opcode")
        self.dispatch = dispatch

    def _get_method(self, name, argcodes):
        #
        def handler(code, position):
            args = ()
            for argcode, argtype in arg_codes_and_types:
                if argcode == 'i':
                    value = self.registers_i[ord(code[position])]
                    position += 1
                    args += (value,)
                    assert argtype == 'i'
                else:
                    raise AssertionError("bad arg code: %r" % (argcode,))
            result = boundmethod(*args)
            if resulttype == 'i':
                assert type(result) is int
                self.registers_i[ord(code[position])] = result
                position += 1
            else:
                assert resulttype is None
                assert result is None
            return position
        #
        boundmethod = getattr(self, 'opimpl_' + name)
        argtypes = boundmethod.argtypes
        resulttype = boundmethod.resulttype
        if resulttype is not None:
            assert argcodes[-1] == 'i'
            argcodes = argcodes[:-1]
        assert len(argcodes) == len(argtypes)
        arg_codes_and_types = unrolling_iterable(zip(argcodes, argtypes))
        handler = func_with_new_name(handler, 'handler_' + name)
        return handler

    def setarg_i(self, index, value):
        self.registers_i[index] = value

    def run(self, jitcode, position):
        code = jitcode.code
        constants = jitcode.constants
        try:
            while True:
                position = self.dispatch(code, position)
        except LeaveFrame:
            pass

    # ----------

    @arguments("i", "i", returns="i")
    def opimpl_int_add(self, a, b):
        return a + b

    @arguments("i")
    def opimpl_int_return(self, a):
        self.result_i = a
        raise LeaveFrame
