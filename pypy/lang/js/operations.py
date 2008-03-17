# encoding: utf-8
"""
operations.py
Implements the javascript operations nodes for the interpretation tree
"""

from pypy.lang.js.jsobj import W_IntNumber, W_FloatNumber, W_Object,\
     w_Undefined, W_NewBuiltin, W_String, create_object, W_List,\
     W_PrimitiveObject, W_Reference, ActivationObject, W_Array, W_Boolean,\
     w_Null, W_BaseNumber, isnull_or_undefined
from pypy.rlib.parsing.ebnfparse import Symbol, Nonterminal
from pypy.lang.js.execution import JsTypeError, ThrowException
from pypy.lang.js.jscode import JsCode, JsFunction
from constants import unescapedict, SLASH

import sys
import os

class Position(object):
    def __init__(self, lineno=-1, start=-1, end=-1):
        self.lineno = lineno
        self.start = start
        self.end = end

    
class Node(object):
    """
    Node is the base class for all the other nodes.
    """
    def __init__(self, pos):
        """
        Initializes the content from the AST specific for each node type
        """
        raise NotImplementedError

    def emit(self, bytecode):
        """ Emits bytecode
        """
        raise NotImplementedError
    
    def get_literal(self):
        raise NotImplementedError
    
    def get_args(self, ctx):
        raise NotImplementedError
    
    def __str__(self):
        return "%s()"%(self.__class__)

class Statement(Node):
    def __init__(self, pos):
        self.pos = pos

class Expression(Statement):
    def execute(self, ctx):
        return self.eval(ctx)

class ListOp(Expression):
    def __init__(self, pos, nodes):
        self.pos = pos
        self.nodes = nodes
        
class UnaryOp(Expression):
    def __init__(self, pos, expr, postfix=False):
        self.pos = pos
        self.expr = expr
        self.postfix = postfix

    def emit(self, bytecode):
        self.expr.emit(bytecode)
        bytecode.emit(self.operation_name)

class BinaryOp(Expression):
    def __init__(self, pos, left, right):
        self.pos = pos
        self.left = left
        self.right = right

    def emit(self, bytecode):
        self.left.emit(bytecode)
        self.right.emit(bytecode)
        bytecode.emit(self.operation_name)

class Undefined(Statement):
    def emit(self, bytecode):
        bytecode.emit('LOAD_UNDEFINED')

class PropertyInit(Expression):
    def __init__(self, pos, lefthand, expr):
        self.pos = pos
        self.lefthand = lefthand
        self.expr = expr
    
    def emit(self, bytecode):
        self.expr.emit(bytecode)
        if isinstance(self.lefthand, Identifier):
            bytecode.emit('LOAD_STRINGCONSTANT', self.lefthand.name)
        else:
            self.lefthand.emit(bytecode)

class Array(ListOp):
    def emit(self, bytecode):
        for element in self.nodes:
            element.emit(bytecode)
        bytecode.emit('LOAD_ARRAY', len(self.nodes))

class Assignment(Expression):
    pass

class SimpleAssignment(Assignment):
    def __init__(self, pos, left, right, operand):
        assert isinstance(left, Identifier)
        self.identifier = left.name
        self.right = right
        self.pos = pos
        self.operand = operand

    def emit(self, bytecode):
        self.right.emit(bytecode)
        bytecode.emit('STORE', self.identifier)

class MemberAssignment(Assignment):
    def __init__(self, pos, what, item, right, operand):
        # XXX we can optimise here what happens if what is identifier,
        #     but let's leave it alone for now
        self.pos = pos
        self.what = what
        self.item = item
        self.right = right
        self.operand = operand

    def emit(self, bytecode):
        self.right.emit(bytecode)
        self.item.emit(bytecode)
        self.what.emit(bytecode)
        bytecode.emit('STORE_MEMBER')

class MemberDotAssignment(Assignment):
    def __init__(self, pos, what, name, right, operand):
        self.pos = pos
        self.what = what
        self.itemname = name
        self.right = right
        self.operand = operand

    def emit(self, bytecode):
        self.right.emit(bytecode)
        bytecode.emit('LOAD_STRINGCONSTANT', self.itemname)
        self.what.emit(bytecode)
        bytecode.emit('STORE_MEMBER')

class StuffAssignment(Expression):
    def __init__(self, pos, left, right, operand):
        self.pos = pos
        # check the sanity of lefthandside
        if isinstance(left, Identifier):
            self.identifier = left.name
            self.single_assignement = True
        elif isinstance(left, Member):
            import pdb
            pdb.set_trace()
            self.lefthandside = left
            self.single_assignement = False
        self.right = right
        self.operand = operand

    def emit(self, bytecode):
        op = self.operand
        if op == '==':
            bytecode.emit('STORE', self.identifier)
        else:
            XXX

    def eval(self, ctx):
        v1 = self.left.eval(ctx)
        v3 = self.right.eval(ctx).GetValue()
        op = self.type
        if op == "=":
            val = v3
        elif op == "*=":
            val = mult(ctx, v1.GetValue(), v3)
        elif op == "+=":
            val = plus(ctx, v1.GetValue(), v3)
        elif op == "-=":
            val = sub(ctx, v1.GetValue(), v3)
        elif op == "/=":
            val = division(ctx, v1.GetValue(), v3)
        elif op == "%=":
            val = mod(ctx, v1.GetValue(), v3)
        elif op == "&=":
            val = W_IntNumber(v1.GetValue().ToInt32() & v3.ToInt32())
        elif op == "|=":
            val = W_IntNumber(v1.GetValue().ToInt32() | v3.ToInt32())
        elif op == "^=":
            val = W_IntNumber(v1.GetValue().ToInt32() ^ v3.ToInt32())
        else:
            print op
            raise NotImplementedError()
        
        v1.PutValue(val, ctx)
        return val
    

class Block(Statement):
    def __init__(self, pos, nodes):
        self.pos = pos
        self.nodes = nodes

    def emit(self, bytecode):
        for node in self.nodes:
            node.emit(bytecode)
            bytecode.emit('POP')
    
    def execute(self, ctx):
        try:
            last = w_Undefined
            for node in self.nodes:
                last = node.execute(ctx)
            return last
        except ExecutionReturned, e:
            if e.type == 'return':
                return e.value
            else:
                raise e
    

class BitwiseAnd(BinaryOp):
    def decision(self, ctx, op1, op2):
        return W_IntNumber(op1&op2)
    

class BitwiseNot(UnaryOp):
    def eval(self, ctx):
        op1 = self.expr.eval(ctx).GetValue().ToInt32()
        return W_IntNumber(~op1)
    

class BitwiseOr(BinaryOp):
    def decision(self, ctx, op1, op2):
        return W_IntNumber(op1|op2)
    


class BitwiseXor(BinaryOp):
    def decision(self, ctx, op1, op2):
        return W_IntNumber(op1^op2)
    

class Unconditional(Statement):
    def __init__(self, pos, target):
        self.pos = pos
        self.target = target
    
class Break(Unconditional):
    def execute(self, ctx):
        raise ExecutionReturned('break', None, None)
    

class Continue(Unconditional):
    def execute(self, ctx):
        raise ExecutionReturned('continue', None, None)
    


class Call(Expression):
    def __init__(self, pos, left, args):
        self.pos = pos
        self.left = left
        self.args = args
    
    def emit(self, bytecode):
        self.args.emit(bytecode)
        self.left.emit(bytecode)
        bytecode.emit('CALL')

class Comma(BinaryOp):
    def eval(self, ctx):
        self.left.eval(ctx)
        return self.right.eval(ctx)
    

class Conditional(Expression):
    def __init__(self, pos, condition, truepart, falsepart):
        self.pos = pos
        self.condition = condition
        self.truepart = truepart
        self.falsepart = falsepart
    
    def eval(self, ctx):
        if self.condition.eval(ctx).GetValue().ToBoolean():
            return self.truepart.eval(ctx).GetValue()
        else:
            return self.falsepart.eval(ctx).GetValue()
    

class Member(Expression):
    "this is for object[name]"
    def __init__(self, pos, left, expr):
        self.pos = pos
        self.left = left
        self.expr = expr

    def emit(self, bytecode):
        self.left.emit(bytecode)
        self.expr.emit(bytecode)
        bytecode.emit('LOAD_ELEMENT')

class MemberDot(BinaryOp):
    "this is for object.name"
    def __init__(self, pos, left, name):
        assert isinstance(name, Identifier)
        self.name = name.name
        self.left = left
        self.pos = pos
    
    def emit(self, bytecode):
        self.left.emit(bytecode)
        bytecode.emit('LOAD_MEMBER', self.name)    

class FunctionStatement(Statement):
    def __init__(self, pos, name, params, body):
        self.pos = pos
        if name is None:
            self.name = None
        else:
            assert isinstance(name, Identifier)
            self.name = name.name
        self.body = body
        self.params = params

    def emit(self, bytecode):
        code = JsCode()
        if self.body is not None:
            self.body.emit(code)
        funcobj = JsFunction(self.name, self.params, code)
        bytecode.emit('DECLARE_FUNCTION', funcobj)
        if self.name is None:
            bytecode.emit('LOAD_FUNCTION', funcobj)
        #else:
        #    bytecode.emit('LOAD_FUNCTION', funcobj)
        #    bytecode.emit('STORE', self.name)
        #    bytecode.emit('POP')

class Identifier(Expression):
    def __init__(self, pos, name):
        self.pos = pos
        self.name = name

    def emit(self, bytecode):
        bytecode.emit('LOAD_VARIABLE', self.name)
        
    def get_literal(self):
        return self.name
    

class This(Identifier):
    pass
    

class If(Statement):
    def __init__(self, pos, condition, thenpart, elsepart=None):
        self.pos = pos
        self.condition = condition
        self.thenPart = thenpart
        self.elsePart = elsepart

    def emit(self, bytecode):
        self.condition.emit(bytecode)
        one = bytecode.prealocate_label()
        bytecode.emit('JUMP_IF_FALSE', one)
        self.thenPart.emit(bytecode)
        if self.elsePart is not None:
            two = bytecode.prealocate_label()
            bytecode.emit('JUMP', two)
            bytecode.emit('LABEL', one)
            self.elsePart.emit(bytecode)
            bytecode.emit('LABEL', two)
        else:
            bytecode.emit('LABEL', one)

    def execute(self, ctx):
        temp = self.condition.eval(ctx).GetValue()
        if temp.ToBoolean():
            return self.thenPart.execute(ctx)
        else:
            return self.elsePart.execute(ctx)

class Group(UnaryOp):
    def eval(self, ctx):
        return self.expr.eval(ctx)

##############################################################################
#
# Binary logic comparison ops and suporting abstract operation
#
##############################################################################

def ARC(ctx, x, y):
    """
    Implements the Abstract Relational Comparison x < y
    Still not fully to the spec
    """
    # XXX fast path when numbers only
    s1 = x.ToPrimitive(ctx, 'Number')
    s2 = y.ToPrimitive(ctx, 'Number')
    if not (isinstance(s1, W_String) and isinstance(s2, W_String)):
        s4 = s1.ToNumber()
        s5 = s2.ToNumber()
        if isnan(s4) or isnan(s5):
            return -1
        if s4 < s5:
            return 1
        else:
            return 0
    else:
        s4 = s1.ToString(ctx)
        s5 = s2.ToString(ctx)
        if s4 < s5:
            return 1
        if s4 == s5:
            return 0
        return -1

class Or(BinaryOp):
    def eval(self, ctx):
        s2 = self.left.eval(ctx).GetValue()
        if s2.ToBoolean():
            return s2
        s4 = self.right.eval(ctx).GetValue()
        return s4
    

class And(BinaryOp):
    def eval(self, ctx):
        s2 = self.left.eval(ctx).GetValue()
        if not s2.ToBoolean():
            return s2
        s4 = self.right.eval(ctx).GetValue()
        return s4
    

class Ge(BinaryOp):
    operation_name = 'GE'
    def decision(self, ctx, op1, op2):
        s5 = ARC(ctx, op1, op2)
        if s5 in (-1, 1):
            return W_Boolean(False)
        else:
            return W_Boolean(True)
    

class Gt(BinaryOp):
    operation_name = 'GT'
    def decision(self, ctx, op1, op2):
        s5 = ARC(ctx, op2, op1)
        if s5 == -1:
            return W_Boolean(False)
        else:
            return W_Boolean(s5)
    

class Le(BinaryOp):
    operation_name = 'LE'
    def decision(self, ctx, op1, op2):
        s5 = ARC(ctx, op2, op1)
        if s5 in (-1, 1):
            return W_Boolean(False)
        else:
            return W_Boolean(True)
    

class Lt(BinaryOp):
    operation_name = 'LT'
    def decision(self, ctx, op1, op2):
        s5 = ARC(ctx, op1, op2)
        if s5 == -1:
            return W_Boolean(False)
        else:
            return W_Boolean(s5)
    

##############################################################################
#
# Bitwise shifts
#
##############################################################################

class Ursh(BinaryOp):
    def decision(self, ctx, op1, op2):
        a = op1.ToUInt32()
        b = op2.ToUInt32()
        return W_IntNumber(a >> (b & 0x1F))

class Rsh(BinaryOp):
    def decision(self, ctx, op1, op2):
        a = op1.ToInt32()
        b = op2.ToUInt32()
        return W_IntNumber(a >> intmask(b & 0x1F))

class Lsh(BinaryOp):
    def decision(self, ctx, op1, op2):
        a = op1.ToInt32()
        b = op2.ToUInt32()
        return W_IntNumber(a << intmask(b & 0x1F))

##############################################################################
#
# Equality and unequality (== and !=)
#
##############################################################################


def AEC(ctx, x, y):
    """
    Implements the Abstract Equality Comparison x == y
    trying to be fully to the spec
    """
    # XXX think about fast paths here and there
    type1 = x.type()
    type2 = y.type()
    if type1 == type2:
        if type1 == "undefined" or type1 == "null":
            return True
        if type1 == "number":
            n1 = x.ToNumber()
            n2 = y.ToNumber()
            if isnan(n1) or isnan(n2):
                return False
            if n1 == n2:
                return True
            return False
        elif type1 == "string":
            return x.ToString(ctx) == y.ToString(ctx)
        elif type1 == "boolean":
            return x.ToBoolean() == x.ToBoolean()
        return x == y
    else:
        #step 14
        if (type1 == "undefined" and type2 == "null") or \
           (type1 == "null" and type2 == "undefined"):
            return True
        if type1 == "number" and type2 == "string":
            return AEC(ctx, x, W_FloatNumber(y.ToNumber()))
        if type1 == "string" and type2 == "number":
            return AEC(ctx, W_FloatNumber(x.ToNumber()), y)
        if type1 == "boolean":
            return AEC(ctx, W_FloatNumber(x.ToNumber()), y)
        if type2 == "boolean":
            return AEC(ctx, x, W_FloatNumber(y.ToNumber()))
        if (type1 == "string" or type1 == "number") and \
            type2 == "object":
            return AEC(ctx, x, y.ToPrimitive(ctx))
        if (type2 == "string" or type2 == "number") and \
            type1 == "object":
            return AEC(ctx, x.ToPrimitive(ctx), y)
        return False
            
        
    objtype = x.GetValue().type()
    if objtype == y.GetValue().type():
        if objtype == "undefined" or objtype == "null":
            return True
        
    if isinstance(x, W_String) and isinstance(y, W_String):
        r = x.ToString(ctx) == y.ToString(ctx)
    else:
        r = x.ToNumber() == y.ToNumber()
    return r

class Eq(BinaryOp):
    def decision(self, ctx, op1, op2):
        return W_Boolean(AEC(ctx, op1, op2))

class Ne(BinaryOp):
    def decision(self, ctx, op1, op2):
        return W_Boolean(not AEC(ctx, op1, op2))


##############################################################################
#
# Strict Equality and unequality, usually means same place in memory
# or equality for primitive values
#
##############################################################################

def SEC(ctx, x, y):
    """
    Implements the Strict Equality Comparison x === y
    trying to be fully to the spec
    """
    type1 = x.type()
    type2 = y.type()
    if type1 != type2:
        return False
    if type1 == "undefined" or type1 == "null":
        return True
    if type1 == "number":
        n1 = x.ToNumber()
        n2 = y.ToNumber()
        if isnan(n1) or isnan(n2):
            return False
        if n1 == n2:
            return True
        return False
    if type1 == "string":
        return x.ToString(ctx) == y.ToString(ctx)
    if type1 == "boolean":
        return x.ToBoolean() == x.ToBoolean()
    return x == y

class StrictEq(BinaryOp):
    def decision(self, ctx, op1, op2):
        return W_Boolean(SEC(ctx, op1, op2))

class StrictNe(BinaryOp):
    def decision(self, ctx, op1, op2):
        return W_Boolean(not SEC(ctx, op1, op2))
    

class In(BinaryOp):
    """
    The in operator, eg: "property in object"
    """
    def decision(self, ctx, op1, op2):
        if not isinstance(op2, W_Object):
            raise ThrowException(W_String("TypeError"))
        name = op1.ToString(ctx)
        return W_Boolean(op2.HasProperty(name))

class Delete(UnaryOp):
    """
    the delete op, erases properties from objects
    """
    def eval(self, ctx):
        r1 = self.expr.eval(ctx)
        if not isinstance(r1, W_Reference):
            return W_Boolean(True)
        r3 = r1.GetBase()
        r4 = r1.GetPropertyName()
        return W_Boolean(r3.Delete(r4))

class BaseIncrementDecrement(UnaryOp):
    def emit(self, bytecode):
        self.expr.emit(bytecode)
        if self.postfix:
            bytecode.emit('POST' + self.operation_name)
        else:
            bytecode.emit('PRE' + self.operation_name)

class Increment(BaseIncrementDecrement):
    """
    ++value (prefix) and value++ (postfix)
    """
    operation_name = 'INCR'

    def eval(self, ctx):
        # XXX write down fast version
        thing = self.expr.eval(ctx)
        val = thing.GetValue()
        x = val.ToNumber()
        resl = plus(ctx, W_FloatNumber(x), W_IntNumber(1))
        thing.PutValue(resl, ctx)
        if self.postfix:
            return val
        else:
            return resl
        

class Decrement(BaseIncrementDecrement):
    """
    same as increment --value and value --
    """
    operation_name = 'DECR'
    
    def eval(self, ctx):
        # XXX write down hot path
        thing = self.expr.eval(ctx)
        val = thing.GetValue()
        x = val.ToNumber()
        resl = sub(ctx, W_FloatNumber(x), W_IntNumber(1))
        thing.PutValue(resl, ctx)
        if self.postfix:
            return val
        else:
            return resl


class Index(BinaryOp):
    def eval(self, ctx):
        w_obj = self.left.eval(ctx).GetValue().ToObject(ctx)
        name= self.right.eval(ctx).GetValue().ToString(ctx)
        return W_Reference(name, w_obj)

class ArgumentList(ListOp):
    def eval(self, ctx):
        return W_List([node.eval(ctx).GetValue() for node in self.nodes])

    def emit(self, bytecode):
        for node in self.nodes:
            node.emit(bytecode)
        bytecode.emit('LOAD_ARRAY', len(self.nodes))

##############################################################################
#
# Math Ops
#
##############################################################################

class BinaryNumberOp(BinaryOp):
    def eval(self, ctx):
        nleft = self.left.eval(ctx).GetValue().ToPrimitive(ctx, 'Number')
        nright = self.right.eval(ctx).GetValue().ToPrimitive(ctx, 'Number')
        result = self.mathop(ctx, nleft, nright)
        return result
    
    def mathop(self, ctx, n1, n2):
        raise NotImplementedError

def mult(ctx, nleft, nright):
    if isinstance(nleft, W_IntNumber) and isinstance(nright, W_IntNumber):
        ileft = nleft.ToInt32()
        iright = nright.ToInt32()
        try:
            return W_IntNumber(ovfcheck(ileft * iright))
        except OverflowError:
            return W_FloatNumber(float(ileft) * float(iright))
    fleft = nleft.ToNumber()
    fright = nright.ToNumber()
    return W_FloatNumber(fleft * fright)

def mod(ctx, nleft, nright): # XXX this one is really not following spec
    ileft = nleft.ToInt32()
    iright = nright.ToInt32()
    return W_IntNumber(ileft % iright)

def division(ctx, nleft, nright):
    fleft = nleft.ToNumber()
    fright = nright.ToNumber()
    if fright == 0:
        if fleft < 0:
            val = -INFINITY
        elif fleft == 0:
            val = NAN
        else:
            val = INFINITY
    else:
        val = fleft / fright
    return W_FloatNumber(val)

class Plus(BinaryNumberOp):
    operation_name = 'ADD'

class Mult(BinaryNumberOp):
    operation_name = 'MUL'
    def mathop(self, ctx, n1, n2):
        return mult(ctx, n1, n2)


class Mod(BinaryNumberOp):
    operation_name = 'MOD'
    def mathop(self, ctx, n1, n2):
        return mod(ctx, n1, n2)

class Division(BinaryNumberOp):
    def mathop(self, ctx, n1, n2):
        return division(ctx, n1, n2)


class Sub(BinaryNumberOp):
    operation_name = 'SUB'
    
    def mathop(self, ctx, n1, n2):
        return sub(ctx, n1, n2)


class Null(Expression):
    def eval(self, ctx):
        return w_Null


##############################################################################
#
# Value and object creation
#
##############################################################################

def commonnew(ctx, obj, args):
    if not isinstance(obj, W_PrimitiveObject):
        raise ThrowException(W_String('it is not a constructor'))
    try:
        res = obj.Construct(ctx=ctx, args=args)
    except JsTypeError:
        raise ThrowException(W_String('it is not a constructor'))
    return res

class New(UnaryOp):
    def eval(self, ctx):
        x = self.expr.eval(ctx).GetValue()
        return commonnew(ctx, x, [])
    

class NewWithArgs(BinaryOp):
    def eval(self, ctx):
        x = self.left.eval(ctx).GetValue()
        args = self.right.eval(ctx).get_args()
        return commonnew(ctx, x, args)

class BaseNumber(Expression):
    pass
    
class IntNumber(BaseNumber):
    def __init__(self, pos, num):
        self.pos = pos
        self.num = num

    def emit(self, bytecode):
        bytecode.emit('LOAD_INTCONSTANT', self.num)

class FloatNumber(BaseNumber):
    def __init__(self, pos, num):
        self.pos = pos
        self.num = num

    def emit(self, bytecode):
        bytecode.emit('LOAD_FLOATCONSTANT', self.num)

class String(Expression):
    def __init__(self, pos, strval):
        self.pos = pos
        self.strval = self.string_unquote(strval)

    def emit(self, bytecode):
        bytecode.emit('LOAD_STRINGCONSTANT', self.strval)
    
    def string_unquote(self, string):
        # XXX I don't think this works, it's very unlikely IMHO
        #     test it
        temp = []
        stop = len(string)-1
        # XXX proper error
        assert stop >= 0
        last = ""
        
        #removing the begining quotes (" or \')
        if string.startswith('"'):
            singlequote = False
        else:
            singlequote = True

        internalstring = string[1:stop]
        
        for c in internalstring:
            if last == SLASH:
                unescapeseq = unescapedict[last+c]
                temp.append(unescapeseq)
                c = ' ' # Could be anything
            elif c != SLASH:
                temp.append(c)
            last = c
        return ''.join(temp)

class ObjectInit(ListOp):
    def emit(self, bytecode):
        for prop in self.nodes:
            prop.emit(bytecode)
        bytecode.emit('LOAD_OBJECT', len(self.nodes))

class SourceElements(Statement):
    """
    SourceElements nodes are found on each function declaration and in global code
    """
    def __init__(self, pos, var_decl, func_decl, nodes, sourcename = ''):
        self.pos = pos
        self.var_decl = var_decl
        self.func_decl = func_decl
        self.nodes = nodes
        self.sourcename = sourcename

    def emit(self, bytecode):
        for varname in self.var_decl:
            bytecode.emit('DECLARE_VAR', varname)
        for funcname, funccode in self.func_decl.items():
            funccode.emit(bytecode)

        for node in self.nodes:
            node.emit(bytecode)
            # we don't need to pop after certain instructions, let's
            # list them
            if not isinstance(node, Return):
                bytecode.emit('POP')

    def execute(self, ctx):
        for varname in self.var_decl:
            ctx.variable.Put(varname, w_Undefined, dd=True)
        for funcname, funccode in self.func_decl.items():
            ctx.variable.Put(funcname, funccode.eval(ctx))
        node = self
        
        try:
            last = w_Undefined
            for node in self.nodes:
                last = node.execute(ctx)
            return last
        except Exception, e:
            if isinstance(e, ExecutionReturned) and e.type == 'return':
                return e.value
            else:
                # TODO: proper exception handling
                print "%s:%d: %s"%(self.sourcename, node.pos.lineno, node)
                raise
    

class Program(Statement):
    def __init__(self, pos, body):
        self.pos = pos
        self.body = body

    def emit(self, bytecode):
        self.body.emit(bytecode)

class Return(Statement):
    def __init__(self, pos, expr):
        self.pos = pos
        self.expr = expr

    def emit(self, bytecode):
        if self.expr is None:
            bytecode.emit('LOAD_UNDEFINED')
        else:
            self.expr.emit(bytecode)
        bytecode.emit('RETURN')

class Throw(Statement):
    def __init__(self, pos, exp):
        self.pos = pos
        self.exp = exp
    
    def execute(self, ctx):
        raise ThrowException(self.exp.eval(ctx).GetValue())

class Try(Statement):
    def __init__(self, pos, tryblock, catchparam, catchblock, finallyblock):
        self.pos = pos
        self.tryblock = tryblock
        self.catchparam = catchparam
        self.catchblock = catchblock
        self.finallyblock = finallyblock
    
    def execute(self, ctx):
        e = None
        tryresult = w_Undefined
        try:
            tryresult = self.tryblock.execute(ctx)
        except ThrowException, excpt:
            e = excpt
            if self.catchblock is not None:
                obj = W_Object()
                obj.Put(self.catchparam.get_literal(), e.exception)
                ctx.push_object(obj)
                tryresult = self.catchblock.execute(ctx)
                ctx.pop_object()
        
        if self.finallyblock is not None:
            tryresult = self.finallyblock.execute(ctx)
        
        #if there is no catchblock reraise the exception
        if (e is not None) and (self.catchblock is None):
            raise e
        
        return tryresult
    

class Typeof(UnaryOp):
    def eval(self, ctx):
        val = self.expr.eval(ctx)
        if isinstance(val, W_Reference) and val.GetBase() is None:
            return W_String("undefined")
        return W_String(val.GetValue().type())

class VariableDeclaration(Expression):
    def __init__(self, pos, identifier, expr=None):
        self.pos = pos
        assert isinstance(identifier, Identifier)
        self.identifier = identifier.name
        self.expr = expr

    def emit(self, bytecode):
        if self.expr is not None:
            self.expr.emit(bytecode)
        else:
            bytecode.emit('LOAD_UNDEFINED')
        bytecode.emit('STORE', self.identifier)
    
    def eval(self, ctx):
        name = self.identifier.get_literal()
        if self.expr is None:
            ctx.variable.Put(name, w_Undefined, dd=True)
        else:
            ctx.variable.Put(name, self.expr.eval(ctx).GetValue(), dd=True)
        return self.identifier.eval(ctx)
    

class VariableDeclList(Expression):
    def __init__(self, pos, nodes):
        self.pos = pos
        self.nodes = nodes

    def emit(self, bytecode):
        for node in self.nodes:
            node.emit(bytecode)
    
    def eval(self, ctx):
        for var in self.nodes:
            var.eval(ctx)
        return w_Undefined
    
class Variable(Statement):
    def __init__(self, pos, body):
        self.pos = pos
        self.body = body

    def emit(self, bytecode):
        self.body.emit(bytecode)
    
    def execute(self, ctx):
        return self.body.eval(ctx)

class Void(UnaryOp):
    def eval(self, ctx):
        self.expr.eval(ctx)
        return w_Undefined
    

class With(Statement):
    def __init__(self, pos, identifier, body):
        self.pos = pos
        self.identifier = identifier
        self.body = body

    def execute(self, ctx):
        obj = self.identifier.eval(ctx).GetValue().ToObject(ctx)
        ctx.push_object(obj)

        try:
            retval = self.body.execute(ctx)
        finally:
            ctx.pop_object()
        return retval


class WhileBase(Statement):
    def __init__(self, pos, condition, body):
        self.pos = pos
        self.condition = condition
        self.body = body

class Do(WhileBase):
    opcode = 'DO'
    
    def execute(self, ctx):
        try:
            self.body.execute(ctx)
        except ExecutionReturned, e:
            if e.type == 'break':
                return
            elif e.type == 'continue':
                pass
        while self.condition.eval(ctx).ToBoolean():
            try:
                self.body.execute(ctx)
            except ExecutionReturned, e:
                if e.type == 'break':
                    break
                elif e.type == 'continue':
                    continue

    def emit(self, bytecode):
        startlabel = bytecode.emit_label()
        self.body.emit(bytecode)
        self.condition.emit(bytecode)
        bytecode.emit('JUMP_IF_TRUE', startlabel)
    
class While(WhileBase):
    def emit(self, bytecode):
        startlabel = bytecode.emit_label()
        self.condition.emit(bytecode)
        endlabel = bytecode.prealocate_label()
        bytecode.emit('JUMP_IF_FALSE', endlabel)
        self.body.emit(bytecode)
        bytecode.emit('JUMP', startlabel)
        bytecode.emit('LABEL', endlabel)

    def execute(self, ctx):
        while self.condition.eval(ctx).ToBoolean():
            try:
                self.body.execute(ctx)
            except ExecutionReturned, e:
                if e.type == 'break':
                    break
                elif e.type == 'continue':
                    continue
    

class ForVarIn(Statement):
    def __init__(self, pos, vardecl, lobject, body):
        self.pos = pos
        self.vardecl = vardecl
        self.object = lobject
        self.body = body
    
    def execute(self, ctx):
        self.vardecl.eval(ctx)
        obj = self.object.eval(ctx).GetValue().ToObject(ctx)
        for prop in obj.propdict.values():
            if prop.de:
                continue
            iterator = self.vardecl.eval(ctx)
            iterator.PutValue(prop.value, ctx)
            try:
                result = self.body.execute(ctx)
            except ExecutionReturned, e:
                if e.type == 'break':
                    break
                elif e.type == 'continue':
                    continue
    

class ForIn(Statement):
    def __init__(self, pos, iterator, lobject, body):
        self.pos = pos
        #assert isinstance(iterator, Node)
        self.iterator = iterator
        self.object = lobject
        self.body = body

    def execute(self, ctx):
        obj = self.object.eval(ctx).GetValue().ToObject(ctx)
        for prop in obj.propdict.values():
            if prop.de:
                continue
            iterator = self.iterator.eval(ctx)
            iterator.PutValue(prop.value, ctx)
            try:
                result = self.body.execute(ctx)
            except ExecutionReturned, e:
                if e.type == 'break':
                    break
                elif e.type == 'continue':
                    continue
    

class For(Statement):
    def __init__(self, pos, setup, condition, update, body):
        self.pos = pos
        self.setup = setup
        self.condition = condition
        self.update = update
        self.body = body
    
    def execute(self, ctx):
        self.setup.eval(ctx).GetValue()
        while self.condition.eval(ctx).ToBoolean():
            try:
                self.body.execute(ctx)
                self.update.eval(ctx)
            except ExecutionReturned, e:
                if e.type == 'break':
                    break
                elif e.type == 'continue':
                    self.update.eval(ctx)
                    continue
    
class Boolean(Expression):
    def __init__(self, pos, boolval):
        self.pos = pos
        self.bool = boolval
    
    def eval(self, ctx):
        return W_Boolean(self.bool)
    

class Not(UnaryOp):
    def eval(self, ctx):
        return W_Boolean(not self.expr.eval(ctx).GetValue().ToBoolean())
    

class UMinus(UnaryOp):
    operation_name = 'UMINUS'
    
    def eval(self, ctx):
        res = self.expr.eval(ctx)
        if isinstance(res, W_IntNumber):
            return W_IntNumber(-res.intval)
        elif isinstance(res, W_FloatNumber):
            return W_FloatNumber(-res.floatval)
        return W_FloatNumber(-self.expr.eval(ctx).GetValue().ToNumber())

class UPlus(UnaryOp):
    operation_name = 'UPLUS'
    
    def eval(self, ctx):
        res = self.expr.eval(ctx)
        if isinstance(res, W_BaseNumber):
            return res
        return W_FloatNumber(self.expr.eval(ctx).GetValue().ToNumber())
    
