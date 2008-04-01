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
from pypy.rlib.unroll import unrolling_iterable

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

class ExprStatement(Node):
    def __init__(self, pos, expr):
        self.pos = pos
        self.expr = expr

    def emit(self, bytecode):
        self.expr.emit(bytecode)
        bytecode.emit('POP')

class Expression(Statement):
    def execute(self, ctx):
        return self.eval(ctx)

class ListOp(Expression):
    def __init__(self, pos, nodes):
        self.pos = pos
        self.nodes = nodes

def create_unary_op(name):
    class UnaryOp(Expression):
        def __init__(self, pos, expr, postfix=False):
            self.pos = pos
            self.expr = expr
            self.postfix = postfix

        def emit(self, bytecode):
            self.expr.emit(bytecode)
            bytecode.emit(name)
    UnaryOp.__name__ = name
    return UnaryOp

def create_binary_op(name):
    class BinaryOp(Expression):
        def __init__(self, pos, left, right):
            self.pos = pos
            self.left = left
            self.right = right

        def emit(self, bytecode):
            self.left.emit(bytecode)
            self.right.emit(bytecode)
            bytecode.emit(name)
    BinaryOp.__name__ = name
    return BinaryOp

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
    def _get_name(self):
        addoper = OPERANDS[self.operand]
        if addoper:
            addoper = '_' + self.prefix.upper() + addoper
        return addoper

OPERANDS = {
    '='  : '',
    '+=' : 'ADD',
    '-=' : 'SUB',
    '*=' : 'MUL',
    '/=' : 'DIV',
    '++' : 'INCR',
    '--' : 'DECR',
    }

class SimpleIncrement(Expression):
    def __init__(self, pos, left, atype):
        self.pos   = pos
        self.left  = left
        self.atype = atype

    def emit(self, bytecode):
        self.left.emit(bytecode)
        if self.atype == '++':
            bytecode.emit('INCR')
        elif self.atype == '--':
            bytecode.emit('DECR')

class SimpleAssignment(Assignment):
    def __init__(self, pos, left, right, operand, prefix=''):
        self.identifier = left.get_literal()
        self.right = right
        self.pos = pos
        self.operand = operand
        self.prefix = prefix

    def emit(self, bytecode):
        if self.right is not None:
            self.right.emit(bytecode)
        bytecode_name = 'STORE' + self._get_name()
        bytecode.emit(bytecode_name, self.identifier)

class VariableAssignment(Assignment):
    def __init__(self, pos, left, right, operand):
        xxx # shall never land here for now
        self.identifier = left.identifier
        self.right = right
        self.pos = pos
        self.operand = operand
        self.depth = left.depth

    def emit(self, bytecode):
        self.right.emit(bytecode)
        bytecode.emit('STORE_VAR', self.depth, self.identifier)

class MemberAssignment(Assignment):
    def __init__(self, pos, what, item, right, operand, prefix=''):
        # XXX we can optimise here what happens if what is identifier,
        #     but let's leave it alone for now
        self.pos = pos
        self.what = what
        self.item = item
        self.right = right
        self.operand = operand
        self.prefix = prefix

    def emit(self, bytecode):
        if self.right is not None:
            self.right.emit(bytecode)
        self.item.emit(bytecode)
        self.what.emit(bytecode)
        bytecode.emit('STORE_MEMBER' + self._get_name())

class MemberDotAssignment(Assignment):
    def __init__(self, pos, what, name, right, operand, prefix=''):
        self.pos = pos
        self.what = what
        self.itemname = name
        self.right = right
        self.operand = operand
        self.prefix = prefix

    def emit(self, bytecode):
        if self.right is not None:
            self.right.emit(bytecode)
        bytecode.emit('LOAD_STRINGCONSTANT', self.itemname)
        self.what.emit(bytecode)
        bytecode.emit('STORE_MEMBER' + self._get_name())

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
    
BitwiseAnd = create_binary_op('BITAND')    

#class BitwiseNot(UnaryOp):
#    def eval(self, ctx):
#        op1 = self.expr.eval(ctx).GetValue().ToInt32()
#        return W_IntNumber(~op1)
    

# class BitwiseOr(BinaryOp):
#     def decision(self, ctx, op1, op2):
#         return W_IntNumber(op1|op2)
    


# class BitwiseXor(BinaryOp):
#     def decision(self, ctx, op1, op2):
#         return W_IntNumber(op1^op2)
    

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

Comma = create_binary_op('COMMA')    

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

class MemberDot(Expression):
    "this is for object.name"
    def __init__(self, pos, left, name):
        self.name = name.get_literal()
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
            self.name = name.get_literal()
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

#class Group(UnaryOp):
#    def eval(self, ctx):
#        return self.expr.eval(ctx)

##############################################################################
#
# Binary logic comparison ops and suporting abstract operation
#
##############################################################################

class And(Expression):
    def __init__(self, pos, left, right):
        self.pos = pos
        self.left = left
        self.right = right
    
    def emit(self, bytecode):
        self.left.emit(bytecode)
        one = bytecode.prealocate_label()
        bytecode.emit('JUMP_IF_FALSE_NOPOP', one)
        self.right.emit(bytecode)
        bytecode.emit('LABEL', one)

class Or(Expression):
    def __init__(self, pos, left, right):
        self.pos = pos
        self.left = left
        self.right = right

    def emit(self, bytecode):
        self.left.emit(bytecode)
        one = bytecode.prealocate_label()
        bytecode.emit('JUMP_IF_TRUE_NOPOP', one)
        self.right.emit(bytecode)
        bytecode.emit('LABEL', one)        
        
Ge = create_binary_op('GE')
Gt = create_binary_op('GT')    
Le = create_binary_op('LE')    
Lt = create_binary_op('LT')        

##############################################################################
#
# Bitwise shifts
#
##############################################################################

# class Ursh(BinaryOp):
#     def decision(self, ctx, op1, op2):
#         a = op1.ToUInt32()
#         b = op2.ToUInt32()
#         return W_IntNumber(a >> (b & 0x1F))

# class Rsh(BinaryOp):
#     def decision(self, ctx, op1, op2):
#         a = op1.ToInt32()
#         b = op2.ToUInt32()
#         return W_IntNumber(a >> intmask(b & 0x1F))

# class Lsh(BinaryOp):
#     def decision(self, ctx, op1, op2):
#         a = op1.ToInt32()
#         b = op2.ToUInt32()
#         return W_IntNumber(a << intmask(b & 0x1F))

##############################################################################
#
# Equality and unequality (== and !=)
#
##############################################################################

Eq = create_binary_op('EQ')
Ne = create_binary_op('NE')

##############################################################################
#
# Strict Equality and unequality, usually means same place in memory
# or equality for primitive values
#
##############################################################################

StrictEq = create_binary_op('IS')
StrictNe = create_binary_op('ISNOT')    

# class In(BinaryOp):
#     """
#     The in operator, eg: "property in object"
#     """
#     def decision(self, ctx, op1, op2):
#         if not isinstance(op2, W_Object):
#             raise ThrowException(W_String("TypeError"))
#         name = op1.ToString(ctx)
#         return W_Boolean(op2.HasProperty(name))

# class Delete(UnaryOp):
#     """
#     the delete op, erases properties from objects
#     """
#     def eval(self, ctx):
#         r1 = self.expr.eval(ctx)
#         if not isinstance(r1, W_Reference):
#             return W_Boolean(True)
#         r3 = r1.GetBase()
#         r4 = r1.GetPropertyName()
#         return W_Boolean(r3.Delete(r4))

#class Index(BinaryOp):
#    def eval(self, ctx):
#        w_obj = self.left.eval(ctx).GetValue().ToObject(ctx)
#        name= self.right.eval(ctx).GetValue().ToString(ctx)
#        return W_Reference(name, w_obj)

class ArgumentList(ListOp):
    def emit(self, bytecode):
        for node in self.nodes:
            node.emit(bytecode)
        bytecode.emit('LOAD_LIST', len(self.nodes))

##############################################################################
#
# Math Ops
#
##############################################################################

Plus = create_binary_op('ADD')
Mult = create_binary_op('MUL')
Mod = create_binary_op('MOD')
Division = create_binary_op('DIV')
Sub = create_binary_op('SUB')

class Null(Expression):
    def eval(self, ctx):
        return w_Null


##############################################################################
#
# Value and object creation
#
##############################################################################

#class New(UnaryOp):
#    def eval(self, ctx):
#        x = self.expr.eval(ctx).GetValue()
#        return commonnew(ctx, x, [])
    
class NewWithArgs(Expression):
    def __init__(self, pos, left, right):
        self.pos = pos
        self.left = left
        self.right = right
    
    def emit(self, bytecode):
        self.left.emit(bytecode)
        self.right.emit(bytecode)
        bytecode.emit('NEW')

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

    def emit(self, bytecode):
        self.exp.emit(bytecode)
        bytecode.emit('THROW')

class Try(Statement):
    def __init__(self, pos, tryblock, catchparam, catchblock, finallyblock):
        self.pos = pos
        self.tryblock = tryblock
        self.catchparam = catchparam
        self.catchblock = catchblock
        self.finallyblock = finallyblock

    def emit(self, bytecode):
        # a bit naive operator for now
        trycode = JsCode()
        self.tryblock.emit(trycode)
        if self.catchblock:
            catchcode = JsCode()
            self.catchblock.emit(catchcode)
        else:
            catchcode = None
        if self.finallyblock:
            finallycode = JsCode()
            self.finallyblock.emit(finallycode)
        else:
            finallycode = None
        bytecode.emit('TRYCATCHBLOCK', trycode, self.catchparam.get_literal(),
                      catchcode, finallycode)    

#class Typeof(UnaryOp):
#    def eval(self, ctx):
#        val = self.expr.eval(ctx)
#        if isinstance(val, W_Reference) and val.GetBase() is None:
#            return W_String("undefined")
#        return W_String(val.GetValue().type())

class VariableDeclaration(Expression):
    def __init__(self, pos, identifier, expr=None):
        self.pos = pos
        self.identifier = identifier.get_literal()
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

class VariableIdentifier(Expression):
    def __init__(self, pos, depth, identifier):
        self.pos = pos
        self.depth = depth
        self.identifier = identifier

    def emit(self, bytecode):
        bytecode.emit('LOAD_REALVAR', self.depth, self.identifier)

    def get_literal(self):
        return self.identifier

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
        bytecode.emit('POP')
    
    def execute(self, ctx):
        return self.body.eval(ctx)

#class Void(UnaryOp):
#    def eval(self, ctx):
#        self.expr.eval(ctx)
#        return w_Undefined
    

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
    

#class Not(UnaryOp):
#    def eval(self, ctx):
#        return W_Boolean(not self.expr.eval(ctx).GetValue().ToBoolean())

UMinus = create_unary_op('UMINUS')
UPlus = create_unary_op('UPLUS')

unrolling_classes = unrolling_iterable((If, Return, Block, While))
