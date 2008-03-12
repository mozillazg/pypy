
from pypy.lang.js.jsobj import W_IntNumber, W_FloatNumber, W_String

class JsCode(object):
    """ That object stands for code of a single javascript function
    """
    def __init__(self):
        self.opcodes = []

    def emit(self, operation, *args):
        try:
            self.opcodes.append(OpcodeMap[operation](*args))
        except KeyError:
            raise ValueError("Unknown opcode %s" % (operation,))
    emit._annspecialcase_ = 'specialize:arg(1)'

    def __repr__(self):
        return "\n".join([repr(i) for i in self.opcodes])

    def __eq__(self, list_of_opcodes):
        if len(list_of_opcodes) != len(self.opcodes):
            return False
        return all([i == j for i, j in zip(self.opcodes, list_of_opcodes)])

class Opcode(object):
    def eval(self, ctx, stack):
        """ Execute in context ctx
        """
        raise NotImplementedError

    def __eq__(self, other):
        return repr(self) == other

    def __repr__(self):
        return self.__class__.__name__

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

class BaseBinaryOperation(Opcode):
    pass

class BaseUnaryOperation(Opcode):
    pass

class Undefined(Opcode):
    def eval(self, ctx):
        return w_Undefined
    
    def execute(self, ctx):
        return w_Undefined

class LOAD_INTCONSTANT(Opcode):
    def __init__(self, value):
        self.w_intvalue = W_IntNumber(int(value))

    def eval(self, ctx):
        return self.w_intvalue

    def __repr__(self):
        return 'LOAD_INTCONSTANT %s' % (self.w_intvalue.intval,)

class LOAD_FLOATCONSTANT(Opcode):
    def __init__(self, value):
        self.w_floatvalue = W_FloatNumber(float(value))

    def eval(self, ctx):
        return self.w_floatvalue

    def __repr__(self):
        return 'LOAD_FLOATCONSTANT %s' % (self.w_floatvalue.floatval,)

class LOAD_STRINGCONSTANT(Opcode):
    def __init__(self, value):
        self.w_stringvalue = W_String(value)

    def eval(self, ctx):
        return self.w_stringvalue

    def get_literal(self):
        return W_String(self.strval).ToString()

    def __repr__(self):
        return 'LOAD_STRINGCONSTANT "%s"' % (self.w_stringvalue.strval,)

class LOAD_VARIABLE(Opcode):
    def __init__(self, identifier):
        self.identifier = identifier

    def eval(self, ctx):
        return ctx.resolve_identifier(self.identifier)

    def __repr__(self):
        return 'LOAD_VARIABLE "%s"' % (self.identifier,)

class LOAD_ARRAY(Opcode):
    def __init__(self, counter):
        self.counter = counter

    def eval(self, ctx):
        proto = ctx.get_global().Get('Array').Get('prototype')
        array = W_Array(ctx, Prototype=proto, Class = proto.Class)
        for i in range(len(self.nodes)):
            array.Put(str(i), self.nodes[i].eval(ctx).GetValue())
        return array

    def __repr__(self):
        return 'LOAD_ARRAY %d' % (self.counter,)

class STORE_MEMBER(Opcode):
    def eval(self, ctx):
        XXX

class STORE(Opcode):
    def __init__(self, name):
        self.name = name
    
    def eval(self, ctx):
        XXX

    def __repr__(self):
        return 'STORE "%s"' % self.name

class LOAD_OBJECT(Opcode):
    def __init__(self, listofnames):
        self.listofnames = listofnames

    def __repr__(self):
        return 'LOAD_OBJECT %r' % (self.listofnames,)

class SUB(BaseBinaryOperation):
    pass

class ADD(BaseBinaryOperation):
    pass

class MUL(BaseBinaryOperation):
    pass

class DIV(BaseBinaryOperation):
    pass

class MOD(BaseBinaryOperation):
    pass

class UPLUS(BaseUnaryOperation):
    pass

class UMINUS(BaseUnaryOperation):
    pass

class PREINCR(BaseUnaryOperation):
    pass

class POSTINCR(BaseUnaryOperation):
    pass

class PREDECR(BaseUnaryOperation):
    pass

class POSTDECR(BaseUnaryOperation):
    pass

OpcodeMap = {}

for name, value in locals().items():
    if name.upper() == name and issubclass(value, Opcode):
        OpcodeMap[name] = value

