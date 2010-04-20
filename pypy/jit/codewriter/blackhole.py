from pypy.rlib.unroll import unrolling_iterable
from pypy.rlib.rarithmetic import intmask, LONG_BIT
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

def signedord(c):
    value = ord(c)
    value = intmask(value << (LONG_BIT-8)) >> (LONG_BIT-8)
    return value


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
            assert key.count('/') == 1, "bad key: %r" % (key,)
            name, argcodes = key.split('/')
            all_funcs.append(self._get_method(name, argcodes))
        all_funcs = unrolling_iterable(enumerate(all_funcs))
        #
        def dispatch_loop(code, position):
            while True:
                opcode = ord(code[position])
                position += 1
                for i, func in all_funcs:
                    if opcode == i:
                        position = func(code, position)
                        break
                else:
                    raise AssertionError("bad opcode")
        self.dispatch_loop = dispatch_loop

    def _get_method(self, name, argcodes):
        #
        def handler(code, position):
            args = ()
            next_argcode = 0
            for argtype in argtypes:
                if argtype == 'i':
                    # argcode can be 'i' or 'c'; 'c' stands for a single
                    # signed byte that gives the value of a small constant.
                    argcode = argcodes[next_argcode]
                    next_argcode = next_argcode + 1
                    if argcode == 'i':
                        value = self.registers_i[ord(code[position])]
                    elif argcode == 'c':
                        value = signedord(code[position])
                    else:
                        raise AssertionError("bad argcode")
                    position += 1
                elif argtype == 'L':
                    # argcode should be 'L' too
                    assert argcodes[next_argcode] == 'L'
                    next_argcode = next_argcode + 1
                    value = ord(code[position]) | (ord(code[position+1])<<8)
                    position += 2
                elif argtype == 'pc':
                    value = position
                else:
                    raise AssertionError("bad argtype")
                args += (value,)
            result = boundmethod(*args)
            if resulttype == 'i':
                # argcode should be 'i' too
                assert argcodes[next_argcode] == 'i'
                next_argcode = next_argcode + 1
                self.registers_i[ord(code[position])] = result
                position += 1
            elif resulttype == 'L':
                position = result
            else:
                assert resulttype is None
                assert result is None
            assert next_argcode == len(argcodes)
            return position
        #
        boundmethod = getattr(self, 'opimpl_' + name)
        argtypes = unrolling_iterable(boundmethod.argtypes)
        resulttype = boundmethod.resulttype
        handler = func_with_new_name(handler, 'handler_' + name)
        return handler

    def setarg_i(self, index, value):
        self.registers_i[index] = value

    def run(self, jitcode, position):
        code = jitcode.code
        constants = jitcode.constants
        try:
            self.dispatch_loop(code, position)
        except LeaveFrame:
            pass

    # ----------

    @arguments("i", "i", returns="i")
    def opimpl_int_add(self, a, b):
        return a + b

    @arguments("i", "i", returns="i")
    def opimpl_int_sub(self, a, b):
        return a - b

    @arguments("i")
    def opimpl_int_return(self, a):
        self.result_i = a
        raise LeaveFrame

    @arguments("L", "i", "i", "pc", returns="L")
    def opimpl_goto_if_not_int_gt(self, target, a, b, pc):
        if a > b:
            return pc
        else:
            return target

    @arguments("L", returns="L")
    def opimpl_goto(self, target):
        return target
