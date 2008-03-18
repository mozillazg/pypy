
from pypy.lang.js.jsobj import W_IntNumber, W_FloatNumber, W_String,\
     W_Array, W_PrimitiveObject, W_Reference, ActivationObject,\
     create_object, W_Object, w_Undefined, W_Boolean, newbool,\
     w_True, w_False
from pypy.lang.js.execution import JsTypeError, ReturnException, ThrowException
from pypy.rlib.unroll import unrolling_iterable
from pypy.lang.js.baseop import plus, sub, compare, AbstractEC, StrictEC,\
     compare_e
from pypy.rlib.jit import hint

class AlreadyRun(Exception):
    pass

def run_bytecode(opcodes, ctx, stack, check_stack=True):
    i = 0
    while i < len(opcodes):
        for name, op in opcode_unrolling:
            opcode = opcodes[i]
            opcode = hint(opcode, deepfreeze=True)
            if isinstance(opcode, op):
                opcode.eval(ctx, stack)
                break
        if isinstance(opcode, BaseJump):
            i = opcode.do_jump(stack, i)
        else:
            i += 1
    if check_stack:
        assert not stack


class JsCode(object):
    """ That object stands for code of a single javascript function
    """
    def __init__(self):
        self.opcodes = []
        self.label_count = 0
        self.has_labels = True
        self.stack = []

    def emit_label(self):
        num = self.prealocate_label()
        self.emit('LABEL', num)
        return num

    def prealocate_label(self):
        num = self.label_count
        self.label_count += 1
        return num        

    def emit(self, operation, *args):
        opcode = None
        for name, opcodeclass in opcode_unrolling:
            if operation == name:
                opcode = opcodeclass(*args)
                self.opcodes.append(opcode)
                return opcode
        raise ValueError("Unknown opcode %s" % (operation,))
    emit._annspecialcase_ = 'specialize:arg(1)'

    def run(self, ctx, check_stack=True):
        if self.has_labels:
            self.remove_labels()
        run_bytecode(self.opcodes, ctx, self.stack, check_stack)

    def remove_labels(self):
        """ Basic optimization to remove all labels and change
        jumps to addresses. Necessary to run code at all
        """
        if not self.has_labels:
            raise AlreadyRun("Already has labels")
        labels = {}
        counter = 0
        for i in range(len(self.opcodes)):
            op = self.opcodes[i]
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

    def run(self, ctx):
        try:
            self.code.run(ctx)
        except ReturnException, e:
            return e.value
        return w_Undefined

class Opcode(object):
    def __init__(self):
        pass
    
    def eval(self, ctx, stack):
        """ Execute in context ctx
        """
        raise NotImplementedError

    def __eq__(self, other):
        return repr(self) == other

    def __repr__(self):
        return self.__class__.__name__

class BaseBinaryComparison(Opcode):
    def eval(self, ctx, stack):
        s4 = stack.pop()#.GetValue()
        s2 = stack.pop()#.GetValue()
        stack.append(self.decision(ctx, s2, s4))

    def decision(self, ctx, op1, op2):
        raise NotImplementedError

class BaseBinaryBitwiseOp(Opcode):
    def eval(self, ctx, stack):
        s5 = stack.pop().ToInt32()#.GetValue().ToInt32()
        s6 = stack.pop().ToInt32()#.GetValue().ToInt32()
        stack.append(self.operation(ctx, s5, s6))
    
    def operation(self, ctx, op1, op2):
        raise NotImplementedError

class BaseBinaryOperation(Opcode):
    def eval(self, ctx, stack):
        right = stack.pop()#.GetValue()
        left = stack.pop()#.GetValue()
        stack.append(self.operation(ctx, left, right))

class BaseUnaryOperation(Opcode):
    pass

class Undefined(Opcode):
    def eval(self, ctx, stack):
        stack.append(w_Undefined)

class LOAD_INTCONSTANT(Opcode):
    def __init__(self, value):
        self.w_intvalue = W_IntNumber(int(value))

    def eval(self, ctx, stack):
        stack.append(self.w_intvalue)

    def __repr__(self):
        return 'LOAD_INTCONSTANT %s' % (self.w_intvalue.intval,)

class LOAD_FLOATCONSTANT(Opcode):
    def __init__(self, value):
        self.w_floatvalue = W_FloatNumber(float(value))

    def eval(self, ctx, stack):
        stack.append(self.w_floatvalue)

    def __repr__(self):
        return 'LOAD_FLOATCONSTANT %s' % (self.w_floatvalue.floatval,)

class LOAD_STRINGCONSTANT(Opcode):
    def __init__(self, value):
        self.w_stringvalue = W_String(value)

    def eval(self, ctx, stack):
        stack.append(self.w_stringvalue)

    #def get_literal(self, ctx):
    #    return W_String(self.strval).ToString(ctx)

    def __repr__(self):
        return 'LOAD_STRINGCONSTANT "%s"' % (self.w_stringvalue.strval,)

class LOAD_UNDEFINED(Opcode):
    def eval(self, ctx, stack):
        stack.append(w_Undefined)

class LOAD_VARIABLE(Opcode):
    def __init__(self, identifier):
        self.identifier = identifier

    def eval(self, ctx, stack):
        stack.append(ctx.resolve_identifier(self.identifier))

    def __repr__(self):
        return 'LOAD_VARIABLE "%s"' % (self.identifier,)

class LOAD_REALVAR(Opcode):
    def __init__(self, depth, identifier):
        self.depth = depth
        self.identifier = identifier

    def eval(self, ctx, stack):
        scope = ctx.scope[self.depth]
        stack.append(scope.Get(self.identifier))
        #stack.append(W_Reference(self.identifier, scope))

    def __repr__(self):
        return 'LOAD_VARIABLE "%s"' % (self.identifier,)

class LOAD_ARRAY(Opcode):
    def __init__(self, counter):
        self.counter = counter

    def eval(self, ctx, stack):
        proto = ctx.get_global().Get('Array').Get('prototype')
        array = W_Array(ctx, Prototype=proto, Class = proto.Class)
        for i in range(self.counter):
            array.Put(str(self.counter - i - 1), stack.pop())#.GetValue())
        stack.append(array)

    def __repr__(self):
        return 'LOAD_ARRAY %d' % (self.counter,)

class LOAD_FUNCTION(Opcode):
    def __init__(self, funcobj):
        self.funcobj = funcobj

    def eval(self, ctx, stack):
        proto = ctx.get_global().Get('Function').Get('prototype')
        w_func = W_Object(ctx=ctx, Prototype=proto, Class='Function',
                          callfunc=self.funcobj)
        w_func.Put('length', W_IntNumber(len(self.funcobj.params)))
        w_obj = create_object(ctx, 'Object')
        w_obj.Put('constructor', w_func, de=True)
        w_func.Put('prototype', w_obj)
        stack.append(w_func)

    def __repr__(self):
        return 'LOAD_FUNCTION' # XXX

class STORE_MEMBER(Opcode):
    pass
    #def eval(self, ctx, ):
    #    XXX

class STORE(Opcode):
    def __init__(self, name):
        self.name = name
    
    def eval(self, ctx, stack):
        value = stack[-1]
        ctx.assign(self.name, value)

    def __repr__(self):
        return 'STORE "%s"' % self.name

class STORE_VAR(Opcode):
    def __init__(self, depth, name):
        self.name = name
        self.depth = depth

    def eval(self, ctx, stack):
        value = stack[-1]
        ctx.scope[self.depth].Put(self.name, value)

    def __repr__(self):
        return 'STORE "%s"' % self.name

class LOAD_OBJECT(Opcode):
    def __init__(self, counter):
        self.counter = counter
    
    def eval(self, ctx, stack):
        w_obj = create_object(ctx, 'Object')
        for _ in range(self.counter):
            name = stack.pop().ToString(ctx)#.GetValue().ToString(ctx)
            w_elem = stack.pop()#.GetValue()
            w_obj.Put(name, w_elem)
        stack.append(w_obj)

    def __repr__(self):
        return 'LOAD_OBJECT %d' % (self.counter,)

class LOAD_MEMBER(Opcode):
    def __init__(self, name):
        self.name = name

    def eval(self, ctx, stack):
        w_obj = stack.pop().ToObject(ctx)#GetValue().ToObject(ctx)
        stack.append(w_obj.Get(self.name))
        #stack.append(W_Reference(self.name, w_obj))

    def __repr__(self):
        return 'LOAD_MEMBER "%s"' % (self.name,)

class LOAD_ELEMENT(Opcode):
    def eval(self, ctx, stack):
        name = stack.pop().ToString(ctx)#GetValue().ToString(ctx)
        w_obj = stack.pop().ToObject(ctx)#GetValue().ToObject(ctx)
        stack.append(w_obj.Get(name))
        #stack.append(W_Reference(name, w_obj))

class COMMA(BaseUnaryOperation):
    def eval(self, ctx, stack):
        one = stack.pop()
        stack.pop()
        stack.append(one)
        # XXX

class SUB(BaseBinaryOperation):
    def operation(self, ctx, left, right):
        return sub(ctx, left, right)

class ADD(BaseBinaryOperation):
    def operation(self, ctx, left, right):
        return plus(ctx, left, right)

class BITAND(BaseBinaryBitwiseOp):
    def operation(self, ctx, op1, op2):
        return W_IntNumber(op1&op2)


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

#class PREINCR(BaseUnaryOperation):
#    pass

#class POSTINCR(BaseUnaryOperation):
#    pass
 
#class PREDECR(BaseUnaryOperation):
#    pass

#class POSTDECR(BaseUnaryOperation):
#    pass

class GT(BaseBinaryComparison):
    def decision(self, ctx, op1, op2):
        return newbool(compare(ctx, op1, op2))

class GE(BaseBinaryComparison):
    def decision(self, ctx, op1, op2):
        return newbool(compare_e(ctx, op1, op2))

class LT(BaseBinaryComparison):
    def decision(self, ctx, op1, op2):
        return newbool(compare(ctx, op2, op1))

class LE(BaseBinaryComparison):
    def decision(self, ctx, op1, op2):
        return newbool(compare_e(ctx, op2, op1))

class EQ(BaseBinaryComparison):
    def decision(self, ctx, op1, op2):
        return newbool(AbstractEC(ctx, op1, op2))

class NE(BaseBinaryComparison):
    def decision(self, ctx, op1, op2):
        return newbool(not AbstractEC(ctx, op1, op2))

class IS(BaseBinaryComparison):
    def decision(self, ctx, op1, op2):
        return newbool(StrictEC(ctx, op1, op2))

class ISNOT(BaseBinaryComparison):
    def decision(self, ctx, op1, op2):
        return newbool(not StrictEC(ctx, op1, op2))

class LABEL(Opcode):
    def __init__(self, num):
        self.num = num

    def __repr__(self):
        return 'LABEL %d' % (self.num,)

class BaseJump(Opcode):
    def __init__(self, where):
        self.where = where
        self.decision = False

    def do_jump(self, stack, pos):
        return 0

    def __repr__(self):
        return '%s %d' % (self.__class__.__name__, self.where)

class JUMP(BaseJump):
    def eval(self, ctx, stack):
        pass

    def do_jump(self, stack, pos):
        return self.where

class BaseIfJump(BaseJump):
    def eval(self, ctx, stack):
        value = stack.pop()
        self.decision = value.ToBoolean()

class BaseIfNopopJump(BaseJump):
    def eval(self, ctx, stack):
        value = stack[-1]
        self.decision = value.ToBoolean()

class JUMP_IF_FALSE(BaseIfJump):
    def do_jump(self, stack, pos):
        if self.decision:
            return pos + 1
        return self.where

class JUMP_IF_FALSE_NOPOP(BaseIfNopopJump):
    def do_jump(self, stack, pos):
        if self.decision:
            stack.pop()
            return pos + 1
        return self.where

class JUMP_IF_TRUE(BaseIfNopopJump):
    def do_jump(self, stack, pos):
        if self.decision:
            return self.where
        return pos + 1

class JUMP_IF_TRUE_NOPOP(BaseIfNopopJump):
    def do_jump(self, stack, pos):
        if self.decision:
            return self.where
        stack.pop()
        return pos + 1

class DECLARE_FUNCTION(Opcode):
    def __init__(self, funcobj):
        self.funcobj = funcobj

    def eval(self, ctx, stack):
        # function declaration actyally don't run anything
        proto = ctx.get_global().Get('Function').Get('prototype')
        w_func = W_Object(ctx=ctx, Prototype=proto, Class='Function', callfunc=self.funcobj)
        w_func.Put('length', W_IntNumber(len(self.funcobj.params)))
        w_obj = create_object(ctx, 'Object')
        w_obj.Put('constructor', w_func, de=True)
        w_func.Put('prototype', w_obj)
        if self.funcobj.name is not None:
            ctx.put(self.funcobj.name, w_func)

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

    def eval(self, ctx, stack):
        ctx.put(self.name, w_Undefined)

    def __repr__(self):
        return 'DECLARE_VAR "%s"' % (self.name,)

class RETURN(Opcode):
    def eval(self, ctx, stack):
        raise ReturnException(stack.pop())

class POP(Opcode):
    def eval(self, ctx, stack):
        stack.pop()

class CALL(Opcode):
    def eval(self, ctx, stack):
        r1 = stack.pop()
        args = stack.pop()
        r3 = r1#.GetValue()
        if not isinstance(r3, W_PrimitiveObject):
            raise ThrowException(W_String("it is not a callable"))
            
        if isinstance(r1, W_Reference):
            r6 = r1.GetBase()
        else:
            r6 = None
        if isinstance(args, ActivationObject):
            r7 = None
        else:
            r7 = r6
        try:
            res = r3.Call(ctx=ctx, args=args.tolist(), this=r7)
        except JsTypeError:
            raise ThrowException(W_String('it is not a function'))
        stack.append(res)

class DUP(Opcode):
    def eval(self, ctx, stack):
        stack.append(stack[-1])

OpcodeMap = {}

for name, value in locals().items():
    if name.upper() == name and issubclass(value, Opcode):
        OpcodeMap[name] = value

opcode_unrolling = unrolling_iterable(OpcodeMap.items())
