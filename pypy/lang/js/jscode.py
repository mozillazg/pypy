
from pypy.lang.js.jsobj import W_IntNumber

class JsCode(object):
    """ That object stands for code of a single javascript function
    """
    def __init__(self):
        self.opcodes = []

    def emit(self, operation, args):
        try:
            self.opcodes.append(OpcodeMap[operation](args))
        except KeyError:
            raise ValueError("Unknown opcode %s" % (operation,))

    def __repr__(self):
        return "\n".join([repr(i) for i in self.opcodes])

    def __eq__(self, list_of_opcodes):
        if len(list_of_opcodes) != len(self.opcodes):
            return False
        return all([i == j for i, j in zip(self.opcodes, list_of_opcodes)])

class Opcode(object):
    def __init__(self, args):
        raise NotImplementedError("Purely abstract")
    
    def eval(self, ctx, stack):
        """ Execute in context ctx
        """
        raise NotImplementedError

    def __eq__(self, other):
        return repr(self) == other

class BaseBinaryComparison(Opcode):
    def eval(self, ctx):
        s2 = self.left.eval(ctx).GetValue()
        s4 = self.right.eval(ctx).GetValue()
        return self.decision(ctx, s2, s4)

    def decision(self, ctx, op1, op2):
        raise NotImplementedError

class BaseBinaryBitwiseOp(Opcode):
    def eval(self, ctx):
        s5 = self.left.eval(ctx).GetValue().ToInt32()
        s6 = self.right.eval(ctx).GetValue().ToInt32()
        return self.decision(ctx, s5, s6)
    
    def decision(self, ctx, op1, op2):
        raise NotImplementedError

class Undefined(Opcode):
    def eval(self, ctx):
        return w_Undefined
    
    def execute(self, ctx):
        return w_Undefined

class LOAD_INTCONSTANT(Opcode):
    def __init__(self, args):
        assert len(args) == 1
        self.w_intvalue = W_IntNumber(int(args[0]))

    def eval(self, ctx):
        return self.w_intvalue

    def __repr__(self):
        return 'LOAD_INTCONSTANT %s' % (self.w_intvalue.intval,)

class LOAD_VARIABLE(Opcode):
    def __init__(self, args):
        assert len(args) == 1
        self.identifier = args[0]

    def eval(self, ctx):
        return ctx.resolve_identifier(self.identifier)

    def __repr__(self):
        return 'LOAD_VARIABLE "%s"' % (self.identifier,)

OpcodeMap = {}

for name, value in locals().items():
    if name.upper() == name and issubclass(value, Opcode):
        OpcodeMap[name] = value

