
from pypy.lang.js.jsobj import W_IntNumber, W_FloatNumber, W_String,\
     W_Array, W_PrimitiveObject, ActivationObject,\
     create_object, W_Object, w_Undefined, newbool,\
     w_True, w_False, W_List, w_Null, W_Iterator, W_Root
import pypy.lang.js.jsobj as jsobj
from pypy.lang.js.execution import JsTypeError, ReturnException, ThrowException
from pypy.rlib.unroll import unrolling_iterable
from pypy.lang.js.baseop import plus, sub, compare, AbstractEC, StrictEC,\
     compare_e, increment, commonnew, mult, division, uminus, mod
from pypy.rlib.jit import hint
from pypy.rlib.rarithmetic import intmask
from pypy.rlib.objectmodel import we_are_translated

class AlreadyRun(Exception):
    pass

def run_bytecode(opcodes, ctx, stack, check_stack=True, retlast=False):
    popped = False
    if retlast:
        if isinstance(opcodes[-1], POP):
            opcodes.pop()
            popped = True
    
    i = 0
    to_pop = 0
    try:
        while i < len(opcodes):
            opcode = opcodes[i]
            #if we_are_translated():
            #    #this is an optimization strategy for translated code
            #    #on top of cpython it destroys the performance
            #    #besides, this code might be completely wrong
            #    for name, op in opcode_unrolling:
            #        opcode = hint(opcode, deepfreeze=True)
            #        if isinstance(opcode, op):
            #            result = opcode.eval(ctx, stack)
            #            assert result is None
            #            break
            #else:
            result = opcode.eval(ctx, stack)
            assert result is None

            if isinstance(opcode, BaseJump):
                i = opcode.do_jump(stack, i)
            else:
                i += 1
            if isinstance(opcode, WITH_START):
                to_pop += 1
            elif isinstance(opcode, WITH_END):
                to_pop -= 1
    finally:
        for i in range(to_pop):
            ctx.pop_object()

    if retlast:
        if popped:
            assert len(stack) == 1
            return stack[0]
        else:
            assert not stack
            return w_Undefined
    if check_stack:
        assert not stack

#def run_bytecode_unguarded(opcodes, ctx, stack, check_stack=True, retlast=False):
#    try:
#        run_bytecode(opcodes, ctx, stack, check_stack, retlast)
#    except ThrowException:
#        print 
#        raise

class T(list):
    def append(self, element):
        assert isinstance(element, W_Root)
        super(T, self).append(element)

class JsCode(object):
    """ That object stands for code of a single javascript function
    """
    def __init__(self):
        self.opcodes = []
        self.label_count = 0
        self.has_labels = True
        self.startlooplabel = []
        self.endlooplabel = []
        self.stack = []

    def emit_label(self, num = -1):
        if num == -1:
            num = self.prealocate_label()
        self.emit('LABEL', num)
        return num

    def emit_startloop_label(self):
        num = self.emit_label()
        self.startlooplabel.append(num)
        return num

    def prealocate_label(self):
        num = self.label_count
        self.label_count += 1
        return num

    def prealocate_endloop_label(self):
        num = self.prealocate_label()
        self.endlooplabel.append(num)
        return num

    def emit_endloop_label(self, label):
        self.endlooplabel.pop()
        self.startlooplabel.pop()
        self.emit_label(label)

    def emit_break(self):
        if not self.endlooplabel:
            raise ThrowException(W_String("Break outside loop"))
        self.emit('JUMP', self.endlooplabel[-1])

    def emit_continue(self):
        if not self.startlooplabel:
            raise ThrowError(W_String("Continue outside loop"))
        self.emit('JUMP', self.startlooplabel[-1])

    def emit(self, operation, *args):
        opcode = getattr(opcodes, operation)(*args)
        self.opcodes.append(opcode)
        return opcode
    emit._annspecialcase_ = 'specialize:arg(1)'

    def emit_store(self, operation, identifier):
        opcode = store_opcodes[operation](identifier)
        self.opcodes.append(opcode)
        return opcode

    def emit_store_member(self, operation):
        opcode = store_member_opcodes[operation]()
        self.opcodes.append(opcode)
        return opcode        

    def run(self, ctx, check_stack=True, retlast=False):
        if self.has_labels:
            self.remove_labels()
        if 1:
            if we_are_translated():
                stack = []
            else:
                stack = T()
            return run_bytecode(self.opcodes, ctx, stack, check_stack,
                                retlast)
        else:
            return run_bytecode_unguarded(self.opcodes, ctx, self,stack,
                                          check_stack, retlast)

    def _freeze_(self):
        if self.has_labels:
            self.remove_labels()
        return True

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
        if not isinstance(list_of_opcodes, list):
            return False
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
        s4 = stack.pop()
        s2 = stack.pop()
        stack.append(self.decision(ctx, s2, s4))

    def decision(self, ctx, op1, op2):
        raise NotImplementedError

class BaseBinaryBitwiseOp(Opcode):
    def eval(self, ctx, stack):
        s5 = stack.pop().ToInt32(ctx)
        s6 = stack.pop().ToInt32(ctx)
        stack.append(self.operation(ctx, s5, s6))

    def operation(self, ctx, op1, op2):
        raise NotImplementedError

class BaseBinaryOperation(Opcode):
    def eval(self, ctx, stack):
        right = stack.pop()
        left = stack.pop()
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

class LOAD_BOOLCONSTANT(Opcode):
    def __init__(self, value):
        self.boolval = value

    def eval(self, ctx, stack):
        stack.append(newbool(self.boolval))

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

class LOAD_NULL(Opcode):
    def eval(self, ctx, stack):
        stack.append(w_Null)

class LOAD_VARIABLE(Opcode):
    def __init__(self, identifier):
        self.identifier = identifier

    def eval(self, ctx, stack):
        stack.append(ctx.resolve_identifier(ctx, self.identifier))

    def __repr__(self):
        return 'LOAD_VARIABLE "%s"' % (self.identifier,)

class LOAD_REALVAR(Opcode):
    def __init__(self, depth, identifier):
        self.depth = depth
        self.identifier = identifier

    def eval(self, ctx, stack):
        raise NotImplementedError()
        # XXX
        # scope = ctx.scope[self.depth]
        # stack.append(scope.Get(ctx, self.identifier))
        #stack.append(W_Reference(self.identifier, scope))

    def __repr__(self):
        return 'LOAD_VARIABLE "%s"' % (self.identifier,)

class LOAD_ARRAY(Opcode):
    def __init__(self, counter):
        self.counter = counter

    def eval(self, ctx, stack):
        proto = ctx.get_global().Get(ctx, 'Array').Get(ctx, 'prototype')
        array = W_Array(ctx, Prototype=proto, Class = proto.Class)
        for i in range(self.counter):
            array.Put(ctx, str(self.counter - i - 1), stack.pop())
        stack.append(array)

    def __repr__(self):
        return 'LOAD_ARRAY %d' % (self.counter,)

class LOAD_LIST(Opcode):
    def __init__(self, counter):
        self.counter = counter

    def eval(self, ctx, stack):
        to_cut = len(stack)-self.counter
        assert to_cut >= 0
        list_w = stack[to_cut:]
        del stack[to_cut:]
        stack.append(W_List(list_w))

    def __repr__(self):
        return 'LOAD_LIST %d' % (self.counter,)

class LOAD_FUNCTION(Opcode):
    def __init__(self, funcobj):
        self.funcobj = funcobj

    def eval(self, ctx, stack):
        proto = ctx.get_global().Get(ctx, 'Function').Get(ctx, 'prototype')
        w_func = W_Object(ctx=ctx, Prototype=proto, Class='Function',
                          callfunc=self.funcobj)
        w_func.Put(ctx, 'length', W_IntNumber(len(self.funcobj.params)))
        w_obj = create_object(ctx, 'Object')
        w_obj.Put(ctx, 'constructor', w_func, flags = jsobj.DE)
        w_func.Put(ctx, 'prototype', w_obj)
        stack.append(w_func)

    def __repr__(self):
        return 'LOAD_FUNCTION' # XXX

# class STORE_VAR(Opcode):
#     def __init__(self, depth, name):
#         self.name = name
#         self.depth = depth

#     def eval(self, ctx, stack):
#         value = stack[-1]
#         ctx.scope[self.depth].Put(ctx, self.name, value)

#     def __repr__(self):
#         return 'STORE_VAR "%s"' % self.name

class LOAD_OBJECT(Opcode):
    def __init__(self, counter):
        self.counter = counter
    
    def eval(self, ctx, stack):
        w_obj = create_object(ctx, 'Object')
        for _ in range(self.counter):
            name = stack.pop().ToString(ctx)
            w_elem = stack.pop()
            w_obj.Put(ctx, name, w_elem)
        stack.append(w_obj)

    def __repr__(self):
        return 'LOAD_OBJECT %d' % (self.counter,)

class LOAD_MEMBER(Opcode):
    def __init__(self, name):
        self.name = name

    def eval(self, ctx, stack):
        w_obj = stack.pop().ToObject(ctx)
        stack.append(w_obj.Get(ctx, self.name))
        #stack.append(W_Reference(self.name, w_obj))

    def __repr__(self):
        return 'LOAD_MEMBER "%s"' % (self.name,)

class LOAD_ELEMENT(Opcode):
    def eval(self, ctx, stack):
        name = stack.pop().ToString(ctx)
        w_obj = stack.pop().ToObject(ctx)
        stack.append(w_obj.Get(ctx, name))
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

class IN(BaseBinaryOperation):
    def operation(self, ctx, left, right):
        if not isinstance(right, W_Object):
            raise ThrowException(W_String("TypeError"))
        name = left.ToString(ctx)
        return newbool(right.HasProperty(name))

class TYPEOF(BaseUnaryOperation):
    def eval(self, ctx, stack):
        one = stack.pop()
        stack.append(W_String(one.type()))

class TYPEOF_VARIABLE(Opcode):
    def __init__(self, name):
        self.name = name

    def eval(self, ctx, stack):
        try:
            var = ctx.resolve_identifier(ctx, self.name)
            stack.append(W_String(var.type()))
        except ThrowException:
            stack.append(W_String('undefined'))

#class Typeof(UnaryOp):
#    def eval(self, ctx):
#        val = self.expr.eval(ctx)
#        if isinstance(val, W_Reference) and val.GetBase() is None:
#            return W_String("undefined")
#        return W_String(val.GetValue().type())


class ADD(BaseBinaryOperation):
    def operation(self, ctx, left, right):
        return plus(ctx, left, right)

class BITAND(BaseBinaryBitwiseOp):
    def operation(self, ctx, op1, op2):
        return W_IntNumber(op1&op2)

class BITXOR(BaseBinaryBitwiseOp):
    def operation(self, ctx, op1, op2):
        return W_IntNumber(op1^op2)

class BITOR(BaseBinaryBitwiseOp):
    def operation(self, ctx, op1, op2):
        return W_IntNumber(op1|op2)

class BITNOT(BaseUnaryOperation):
    def eval(self, ctx, stack):
        op = stack.pop().ToInt32(ctx)
        stack.append(W_IntNumber(~op))

class URSH(BaseBinaryBitwiseOp):
    def eval(self, ctx, stack):
        op2 = stack.pop().ToUInt32(ctx)
        op1 = stack.pop().ToUInt32(ctx)
        stack.append(W_IntNumber(op1 >> (op2 & 0x1F)))

class RSH(BaseBinaryBitwiseOp):
    def eval(self, ctx, stack):
        op2 = stack.pop().ToUInt32(ctx)
        op1 = stack.pop().ToInt32(ctx)
        stack.append(W_IntNumber(op1 >> intmask(op2 & 0x1F)))

class LSH(BaseBinaryBitwiseOp):
    def eval(self, ctx, stack):
        op2 = stack.pop().ToUInt32(ctx)
        op1 = stack.pop().ToInt32(ctx)
        stack.append(W_IntNumber(op1 << intmask(op2 & 0x1F)))

class MUL(BaseBinaryOperation):
    def operation(self, ctx, op1, op2):
        return mult(ctx, op1, op2)

class DIV(BaseBinaryOperation):
    def operation(self, ctx, op1, op2):
        return division(ctx, op1, op2)

class MOD(BaseBinaryOperation):
    def operation(self, ctx, op1, op2):
        return mod(ctx, op1, op2)

class UPLUS(BaseUnaryOperation):
    def eval(self, ctx, stack):
        if isinstance(stack[-1], W_IntNumber):
            return
        if isinstance(stack[-1], W_FloatNumber):
            return
        stack.append(W_FloatNumber(stack.pop().ToNumber(ctx)))

class UMINUS(BaseUnaryOperation):
    def eval(self, ctx, stack):
        stack.append(uminus(stack.pop(), ctx))

class NOT(BaseUnaryOperation):
    def eval(self, ctx, stack):
        stack.append(newbool(not stack.pop().ToBoolean()))

class INCR(BaseUnaryOperation):
    pass

class DECR(BaseUnaryOperation):
    pass

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


class BaseStoreMember(Opcode):
    def eval(self, ctx, stack):
        left = stack.pop()
        elem = stack.pop()
        value = stack.pop()
        name = elem.ToString(ctx)
        value = self.operation(ctx, left, name, value)
        left.ToObject(ctx).Put(ctx, name, value)
        stack.append(value)

class STORE_MEMBER(BaseStoreMember):
    def operation(self, ctx, left, elem, value):
        return value

class BaseStoreMemberAssign(BaseStoreMember):
    def operation(self, ctx, left, name, value):
        prev = left.Get(ctx, name)
        return self.decision(ctx, value, prev)

class STORE_MEMBER_ADD(BaseStoreMemberAssign):
    def decision(self, ctx, value, prev):
        return plus(ctx, value, prev)

class STORE_MEMBER_POSTINCR(BaseStoreMember):
    def operation(self, *args):
        raise NotImplementedError

class STORE_MEMBER_PREINCR(BaseStoreMember):
    def operation(self, *args):
        raise NotImplementedError    

class STORE_MEMBER_SUB(BaseStoreMember):
    def operation(self, *args):
        raise NotImplementedError

class BaseStore(Opcode):
    def __init__(self, name):
        self.name = name
    
    def eval(self, ctx, stack):
        value = self.process(ctx, self.name, stack)
        ctx.assign(self.name, value)

    def __repr__(self):
        return '%s "%s"' % (self.__class__.__name__, self.name)

class STORE(BaseStore):
    def process(self, ctx, name, stack):
        return stack[-1]

class BaseAssignOper(BaseStore):
    def process(self, ctx, name, stack):
        right = stack.pop()
        left = ctx.resolve_identifier(ctx, name)
        result = self.operation(ctx, left, right)
        stack.append(result)
        return result

class BaseAssignBitOper(BaseStore):
    def process(self, ctx, name, stack):
        right = stack.pop().ToInt32(ctx)
        left = ctx.resolve_identifier(ctx, name).ToInt32(ctx)
        result = self.operation(ctx, left, right)
        stack.append(result)
        return result

class STORE_ADD(BaseAssignOper):
    def operation(self, ctx, left, right):
        return plus(ctx, left, right)

class STORE_SUB(BaseAssignOper):
    def operation(self, ctx, left, right):
        return sub(ctx, left, right)

class STORE_MUL(BaseAssignOper):
    def operation(self, ctx, left, right):
        return mult(ctx, left, right)

class STORE_DIV(BaseAssignOper):
    def operation(self, ctx, left, right):
        return division(ctx, left, right)

class STORE_MOD(BaseAssignOper):
    def operation(self, ctx, left, right):
        return mod(ctx, left, right)

class STORE_BITAND(BaseAssignBitOper):
    def operation(self, ctx, op1, op2):
        return W_IntNumber(op1&op2)

class STORE_BITOR(BaseAssignBitOper):
    def operation(self, ctx, op1, op2):
        return W_IntNumber(op1|op2)

class STORE_BITXOR(BaseAssignBitOper):
    def operation(self, ctx, op1, op2):
        return W_IntNumber(op1^op2)

class STORE_POSTINCR(BaseStore):
    def process(self, ctx, name, stack):
        value = ctx.resolve_identifier(ctx, name)
        num = value.ToNumber(ctx)
        newval = W_FloatNumber(num + 1)
        
        stack.append(W_FloatNumber(num))
        return newval

class STORE_POSTDECR(BaseStore):
    def process(self, ctx, name, stack):
        value = ctx.resolve_identifier(ctx, name)
        num = value.ToNumber(ctx)
        newval = W_FloatNumber(num - 1)
        
        stack.append(W_FloatNumber(num))
        return newval

class STORE_PREINCR(BaseStore):
    def process(self, ctx, name, stack):
        value = ctx.resolve_identifier(ctx, name)
        num = value.ToNumber(ctx)
        newval = W_FloatNumber(num + 1)
        
        stack.append(newval)
        return newval

class STORE_PREDECR(BaseStore):
    def process(self, ctx, name, stack):
        value = ctx.resolve_identifier(ctx, name)
        num = value.ToNumber(ctx)
        newval = W_FloatNumber(num - 1)
        
        stack.append(newval)
        return newval

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
        proto = ctx.get_global().Get(ctx, 'Function').Get(ctx, 'prototype')
        w_func = W_Object(ctx=ctx, Prototype=proto, Class='Function', callfunc=self.funcobj)
        w_func.Put(ctx, 'length', W_IntNumber(len(self.funcobj.params)))
        w_obj = create_object(ctx, 'Object')
        w_obj.Put(ctx, 'constructor', w_func, flags = jsobj.DE)
        w_func.Put(ctx, 'prototype', w_obj)
        if self.funcobj.name is not None:
            ctx.scope[-1].Put(ctx, self.funcobj.name, w_func)

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
        ctx.scope[-1].Put(ctx, self.name, w_Undefined, flags = jsobj.DD)

    def __repr__(self):
        return 'DECLARE_VAR "%s"' % (self.name,)

class RETURN(Opcode):
    def eval(self, ctx, stack):
        raise ReturnException(stack.pop())

class POP(Opcode):
    def eval(self, ctx, stack):
        stack.pop()

def common_call(ctx, r1, args, this, name):
    if not isinstance(r1, W_PrimitiveObject):
        raise ThrowException(W_String("%s is not a callable (%s)"%(r1.ToString(ctx), name)))
    try:
        res = r1.Call(ctx=ctx, args=args.tolist(), this=this)
    except JsTypeError:
        raise ThrowException(W_String("%s is not a function (%s)"%(r1.ToString(ctx), name)))
    return res

class CALL(Opcode):
    def eval(self, ctx, stack):
        r1 = stack.pop()
        args = stack.pop()
        name = r1.ToString(ctx)
        #XXX hack, this should be comming from context
        stack.append(common_call(ctx, r1, args, ctx.scope[-1], name))

class CALL_METHOD(Opcode):
    def eval(self, ctx, stack):
        method = stack.pop()
        what = stack.pop().ToObject(ctx)
        args = stack.pop()
        name = method.ToString(ctx)
        r1 = what.Get(ctx, name)
        stack.append(common_call(ctx, r1, args, what, name))

class DUP(Opcode):
    def eval(self, ctx, stack):
        stack.append(stack[-1])

class THROW(Opcode):
    def eval(self, ctx, stack):
        val = stack.pop()
        raise ThrowException(val)

class TRYCATCHBLOCK(Opcode):
    def __init__(self, trycode, catchparam, catchcode, finallycode):
        self.trycode     = trycode
        self.catchcode   = catchcode
        self.catchparam  = catchparam
        self.finallycode = finallycode
    
    def eval(self, ctx, stack):
        try:
            try:
                self.trycode.run(ctx)
            except ThrowException, e:
                if self.catchcode is not None:
                    # XXX just copied, I don't know if it's right
                    obj = W_Object()
                    obj.Put(ctx, self.catchparam, e.exception)
                    ctx.push_object(obj)
                    try:
                        self.catchcode.run(ctx)
                    finally:
                        ctx.pop_object()
                if self.finallycode is not None:
                    self.finallycode.run(ctx)
                if not self.catchcode:
                    raise
        except ReturnException:
            # we run finally block here and re-raise the exception
            if self.finallycode is not None:
                self.finallycode.run(ctx)
            raise

    def __repr__(self):
        return "TRYCATCHBLOCK" # XXX shall we add stuff here???

class NEW(Opcode):        
    def eval(self, ctx, stack):
        y = stack.pop()
        x = stack.pop()
        assert isinstance(y, W_List)
        args = y.get_args()
        stack.append(commonnew(ctx, x, args))

class NEW_NO_ARGS(Opcode):
    def eval(self, ctx, stack):
        x = stack.pop()
        stack.append(commonnew(ctx, x, []))

# ------------ iterator support ----------------

class LOAD_ITERATOR(Opcode):
    def eval(self, ctx, stack):
        obj = stack.pop().ToObject(ctx)
        props = [prop.value for prop in obj.propdict.values() if not prop.flags & jsobj.DE]
        stack.append(W_Iterator(props))

class JUMP_IF_ITERATOR_EMPTY(BaseJump):
    def eval(self, ctx, stack):
        pass
    
    def do_jump(self, stack, pos):
        iterator = stack[-1]
        assert isinstance(iterator, W_Iterator)
        if iterator.empty():
            return self.where
        return pos + 1

class NEXT_ITERATOR(Opcode):
    def __init__(self, name):
        self.name = name

    def eval(self, ctx, stack):
        iterator = stack[-1]
        assert isinstance(iterator, W_Iterator)
        ctx.assign(self.name, iterator.next())

# ---------------- with support ---------------------

class WITH_START(Opcode):
    def __init__(self, name):
        self.name = name

    def eval(self, ctx, stack):
        ctx.push_object(ctx.resolve_identifier(ctx, self.name).ToObject(ctx))

class WITH_END(Opcode):
    def eval(self, ctx, stack):
        ctx.pop_object()

# ------------------ delete -------------------------

class DELETE(Opcode):
    def __init__(self, name):
        self.name = name

    def eval(self, ctx, stack):
        stack.append(newbool(ctx.delete_identifier(self.name)))

class DELETE_MEMBER(Opcode):
    def eval(self, ctx, stack):
        what = stack.pop().ToString(ctx)
        obj = stack.pop().ToObject(ctx)
        stack.append(newbool(obj.Delete(what)))

# different opcode mappings, to make annotator happy

OpcodeMap = {}

for name, value in locals().items():
    if name.upper() == name and type(value) == type(Opcode) and issubclass(value, Opcode):
        OpcodeMap[name] = value

opcode_unrolling = unrolling_iterable(OpcodeMap.items())

class Opcodes:
    pass

opcodes = Opcodes()
store_opcodes = {}
store_member_opcodes = {}
for name, value in OpcodeMap.items():
    if name.startswith('STORE_MEMBER'):
        store_member_opcodes[name] = value
    elif name.startswith('STORE'):
        store_opcodes[name] = value
    setattr(opcodes, name, value)
