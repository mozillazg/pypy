
from pypy.lang.js.jsobj import W_IntNumber, W_FloatNumber, W_String

class AlreadyRun(Exception):
    pass

class JsCode(object):
    """ That object stands for code of a single javascript function
    """
    def __init__(self):
        self.opcodes = []
        self.label_count = 0
        self.has_labels = True

    def emit_label(self):
        num = self.prealocate_label()
        self.emit('LABEL', num)
        return num

    def prealocate_label(self):
        num = self.label_count
        self.label_count += 1
        return num        

    def emit(self, operation, *args):
        try:
            opcode = OpcodeMap[operation](*args)
            self.opcodes.append(opcode)
            return opcode
        except KeyError:
            raise ValueError("Unknown opcode %s" % (operation,))
    emit._annspecialcase_ = 'specialize:arg(1)'

    def remove_labels(self):
        """ Basic optimization to remove all labels and change
        jumps to addresses. Necessary to run code at all
        """
        if not self.has_labels:
            raise AlreadyRun("Already has labels")
        labels = {}
        counter = 0
        for i, op in enumerate(self.opcodes):
            if isinstance(op, LABEL):
                labels[op.num] = counter
            else:
                counter += 1
        self.opcodes = [op for op in self.opcodes if not isinstance(op, LABEL)]
        for op in self.opcodes:
            if isinstance(op, BaseJump):
                op.where = labels[op.where]
        self.has_labels = False

    def __repr__(self):
        return "\n".join([repr(i) for i in self.opcodes])

    def __eq__(self, list_of_opcodes):
        if len(list_of_opcodes) != len(self.opcodes):
            return False
        return all([i == j for i, j in zip(self.opcodes, list_of_opcodes)])

class JsFunction(object):
    def __init__(self, name, params, code):
        self.name = name
        self.params = params
        self.code = code

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

class LOAD_FUNCTION(Opcode):
    def __init__(self, funcobj):
        self.funcobj = funcobj

    def __repr__(self):
        return 'LOAD_FUNCTION' # XXX

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

class GT(BaseBinaryComparison):
    pass

class GE(BaseBinaryComparison):
    pass

class LT(BaseBinaryComparison):
    pass

class LE(BaseBinaryComparison):
    pass

class LABEL(Opcode):
    def __init__(self, num):
        self.num = num

    def __repr__(self):
        return 'LABEL %d' % (self.num,)

class BaseJump(Opcode):
    def __init__(self, where):
        self.where = where

    def __repr__(self):
        return '%s %d' % (self.__class__.__name__, self.where)

class JUMP(BaseJump):
    pass

class JUMP_IF_FALSE(BaseJump):
    pass

class JUMP_IF_TRUE(BaseJump):
    pass

class DECLARE_FUNCTION(Opcode):
    def __init__(self, funcobj):
        self.funcobj = funcobj

    def __repr__(self):
        funcobj = self.funcobj
        if funcobj.name is None:
            name = ""
        else:
            name = funcobj.name + " "
        codestr = '\n'.join(['  %r' % (op,) for op in funcobj.code.opcodes])
        return 'DECLARE_FUNCTION %s%r [\n%s\n]' % (name, funcobj.params, codestr)

class DECLARE_VAR(Opcode):
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return 'DECLARE_VAR "%s"' % (self.name,)

class RETURN(Opcode):
    pass

OpcodeMap = {}

for name, value in locals().items():
    if name.upper() == name and issubclass(value, Opcode):
        OpcodeMap[name] = value

