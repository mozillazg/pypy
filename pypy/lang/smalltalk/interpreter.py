import py
from pypy.lang.smalltalk.shadow import ContextPartShadow, MethodContextShadow, BlockContextShadow
from pypy.lang.smalltalk import model, constants, primitives
from pypy.lang.smalltalk.shadow import ContextPartShadow
from pypy.lang.smalltalk.conftest import option
from pypy.rlib import objectmodel, unroll
from pypy.lang.smalltalk import wrapper


class MissingBytecode(Exception):
    """Bytecode not implemented yet."""
    def __init__(self, bytecodename):
        self.bytecodename = bytecodename
        print "MissingBytecode:", bytecodename     # hack for debugging

class IllegalStoreError(Exception):
    """Illegal Store."""

class Interpreter(object):

    _w_last_active_context = None
    cnt = 0
    
    def __init__(self, space, image_name=""):
        self._w_active_context = None
        self.space = space
        self.image_name = image_name

    def w_active_context(self):
        return self._w_active_context

    def store_w_active_context(self, w_context):
        assert isinstance(w_context, model.W_PointersObject)
        self._w_active_context = w_context

    def s_active_context(self):
        return self.w_active_context().as_context_get_shadow(self.space)

    def interpret(self):
        try:
            while True:
                self.step()
        except ReturnFromTopLevel, e:
            return e.object

    def should_trace(self, primitives=False):
        if objectmodel.we_are_translated():
            return False
        if not primitives:
            return option.bc_trace
        return option.prim_trace

    def step(self):
        s_active_context = self.s_active_context()
        next = s_active_context.getNextBytecode()
        # we_are_translated returns false on top of CPython and true when
        # translating the interpreter
        if not objectmodel.we_are_translated():
            bytecodeimpl = BYTECODE_TABLE[next]

            if self.should_trace():
                if self._w_last_active_context != self.w_active_context():
                    cnt = 0
                    p = self.w_active_context()
                    # AK make method
                    while not p.is_same_object(self.space.w_nil):
                        cnt += 1
                                                  # Do not update the context
                                                  # for this action.
                        p = p.as_context_get_shadow(self.space).w_sender()
                    self._last_indent = "  " * cnt
                    self._w_last_active_context = self.w_active_context()

                print "%sStack=%s" % (
                    self._last_indent,
                    repr(s_active_context.stack()),)
                print "%sBytecode at %d (%d:%s):" % (
                    self._last_indent,
                    s_active_context.pc(),
                    next, bytecodeimpl.__name__,)

            bytecodeimpl(s_active_context, self)

        else:
            bytecode_dispatch_translated(self, s_active_context, next)

        
class ReturnFromTopLevel(Exception):
    def __init__(self, object):
        self.object = object

def make_call_primitive_bytecode(primitive, selector, argcount):
    def callPrimitive(self, interp):
        # WARNING: this is used for bytecodes for which it is safe to
        # directly call the primitive.  In general, it is not safe: for
        # example, depending on the type of the receiver, bytecodePrimAt
        # may invoke primitives.AT, primitives.STRING_AT, or anything
        # else that the user put in a class in an 'at:' method.
        # The rule of thumb is that primitives with only int and float
        # in their unwrap_spec are safe.
        func = primitives.prim_table[primitive]
        try:
            func(interp, argcount)
            return
        except primitives.PrimitiveFailedError:
            pass
        self._sendSelfSelector(selector, argcount, interp)
    return callPrimitive

# ___________________________________________________________________________
# Bytecode Implementations:
#
# "self" is always a ContextPartShadow instance.  

# __extend__ adds new methods to the ContextPartShadow class
class __extend__(ContextPartShadow):
    # push bytecodes
    def pushReceiverVariableBytecode(self, interp):
        index = self.currentBytecode & 15
        self.push(self.w_receiver().fetch(self.space, index))

    def pushTemporaryVariableBytecode(self, interp):
        index = self.currentBytecode & 15
        self.push(self.gettemp(index))

    def pushLiteralConstantBytecode(self, interp):
        index = self.currentBytecode & 31
        self.push(self.w_method().getliteral(index))

    def pushLiteralVariableBytecode(self, interp):
        # this bytecode assumes that literals[index] is an Association
        # which is an object with two named vars, and fetches the second
        # named var (the value).
        index = self.currentBytecode & 31
        w_association = self.w_method().getliteral(index)
        association = wrapper.AssociationWrapper(self.space, w_association)
        self.push(association.value())

    def storeAndPopReceiverVariableBytecode(self, interp):
        index = self.currentBytecode & 7
        self.w_receiver().store(self.space, index, self.pop())

    def storeAndPopTemporaryVariableBytecode(self, interp):
        index = self.currentBytecode & 7
        self.settemp(index, self.pop())

    # push bytecodes
    def pushReceiverBytecode(self, interp):
        self.push(self.w_receiver())

    def pushConstantTrueBytecode(self, interp):
        self.push(interp.space.w_true)

    def pushConstantFalseBytecode(self, interp):
        self.push(interp.space.w_false)

    def pushConstantNilBytecode(self, interp):
        self.push(interp.space.w_nil)

    def pushConstantMinusOneBytecode(self, interp):
        self.push(interp.space.w_minus_one)

    def pushConstantZeroBytecode(self, interp):
        self.push(interp.space.w_zero)

    def pushConstantOneBytecode(self, interp):
        self.push(interp.space.w_one)

    def pushConstantTwoBytecode(self, interp):
        self.push(interp.space.w_two)

    def pushActiveContextBytecode(self, interp):
        self.push(self.w_self())

    def duplicateTopBytecode(self, interp):
        self.push(self.top())

    # send, return bytecodes
    def sendLiteralSelectorBytecode(self, interp):
        selector = self.w_method().getliteralsymbol(self.currentBytecode & 15)
        argcount = ((self.currentBytecode >> 4) & 3) - 1
        self._sendSelfSelector(selector, argcount, interp)

    def _sendSelfSelector(self, selector, argcount, interp):
        receiver = self.peek(argcount)
        self._sendSelector(selector, argcount, interp,
                           receiver, receiver.shadow_of_my_class(self.space))

    def _sendSuperSelector(self, selector, argcount, interp):
        w_compiledin = self.w_method().compiledin()
        assert isinstance(w_compiledin, model.W_PointersObject)
        s_compiledin = w_compiledin.as_class_get_shadow(self.space)
        self._sendSelector(selector, argcount, interp, self.w_receiver(),
                           s_compiledin.s_superclass())

    def _sendSelector(self, selector, argcount, interp,
                      receiver, receiverclassshadow):
        if interp.should_trace():
            print "%sSending selector %r to %r with: %r" % (
                interp._last_indent, selector, receiver,
                [self.peek(argcount-1-i) for i in range(argcount)])
            pass
        assert argcount >= 0
        method = receiverclassshadow.lookup(selector)
        # XXX catch MethodNotFound here and send doesNotUnderstand:
        # AK shouln't that be done in lookup itself, please check what spec says about DNU in case of super sends.
        if method.primitive:
            # the primitive pushes the result (if any) onto the stack itself
            code = method.primitive
            if interp.should_trace():
                print "%sActually calling primitive %d" % (interp._last_indent, code,)
            if objectmodel.we_are_translated():
                for i, func in primitives.unrolling_prim_table:
                    if i == code:
                        try:
                            func(interp, argcount)
                            return
                        except primitives.PrimitiveFailedError:
                            break
            else:
                func = primitives.prim_table[code]
                try:
                    # note: argcount does not include rcvr
                    w_result = func(interp, argcount)
                    return
                except primitives.PrimitiveFailedError:
                    if interp.should_trace(True):
                        print "PRIMITIVE FAILED: %d %s" % (method.primitive, selector,)
                    pass # ignore this error and fall back to the Smalltalk version
        arguments = self.pop_and_return_n(argcount)
        frame = method.create_frame(self.space, receiver, arguments,
                                    self.w_self())
        interp.store_w_active_context(frame)
        self.pop()

    def _return(self, object, interp, w_return_to):
        # for tests, when returning from the top-level context
        if w_return_to.is_same_object(self.space.w_nil):
            raise ReturnFromTopLevel(object)
        w_return_to.as_context_get_shadow(self.space).push(object)
        interp.store_w_active_context(w_return_to)

    def returnReceiver(self, interp):
        self._return(self.w_receiver(), interp, self.s_home().w_sender())

    def returnTrue(self, interp):
        self._return(interp.space.w_true, interp, self.s_home().w_sender())

    def returnFalse(self, interp):
        self._return(interp.space.w_false, interp, self.s_home().w_sender())

    def returnNil(self, interp):
        self._return(interp.space.w_nil, interp, self.s_home().w_sender())

    def returnTopFromMethod(self, interp):
        self._return(self.top(), interp, self.s_home().w_sender())

    def returnTopFromBlock(self, interp):
        self._return(self.top(), interp, self.w_sender())

    def unknownBytecode(self, interp):
        raise MissingBytecode("unknownBytecode")

    def extendedVariableTypeAndIndex(self):
        # AK please explain this method (a helper, I guess)
        descriptor = self.getbytecode()
        return ((descriptor >> 6) & 3), (descriptor & 63)

    def extendedPushBytecode(self, interp):
        variableType, variableIndex = self.extendedVariableTypeAndIndex()
        if variableType == 0:
            self.push(self.w_receiver().fetch(self.space, variableIndex))
        elif variableType == 1:
            self.push(self.gettemp(variableIndex))
        elif variableType == 2:
            self.push(self.w_method().getliteral(variableIndex))
        elif variableType == 3:
            w_association = self.w_method().getliteral(variableIndex)
            association = wrapper.AssociationWrapper(self.space, w_association)
            self.push(association.value())
        else:
            assert 0
        
    def extendedStoreBytecode(self, interp):
        variableType, variableIndex = self.extendedVariableTypeAndIndex()
        if variableType == 0:
            self.w_receiver().store(self.space, variableIndex, self.top())
        elif variableType == 1:
            self.settemp(variableIndex, self.top())
        elif variableType == 2:
            raise IllegalStoreError
        elif variableType == 3:
            w_association = self.w_method().getliteral(variableIndex)
            association = wrapper.AssociationWrapper(self.space, w_association)
            association.store_value(self.top())

    def extendedStoreAndPopBytecode(self, interp):
        self.extendedStoreBytecode(interp)
        self.pop()

    def getExtendedSelectorArgcount(self):
        descriptor = self.getbytecode()
        return ((self.w_method().getliteralsymbol(descriptor & 31)),
                (descriptor >> 5))

    def singleExtendedSendBytecode(self, interp):
        selector, argcount = self.getExtendedSelectorArgcount()
        self._sendSelfSelector(selector, argcount, interp)

    def doubleExtendedDoAnythingBytecode(self, interp):
        second = self.getbytecode()
        third = self.getbytecode()
        opType = second >> 5
        if opType == 0:
            # selfsend
            self._sendSelfSelector(self.w_method().getliteralsymbol(third),
                                   second & 31, interp)
        elif opType == 1:
            # supersend
            self._sendSuperSelector(self.w_method().getliteralsymbol(third),
                                    second & 31, interp)
        elif opType == 2:
            # pushReceiver
            self.push(self.w_receiver().fetch(self.space, third))
        elif opType == 3:
            # pushLiteralConstant
            self.push(self.w_method().getliteral(third))
        elif opType == 4:
            # pushLiteralVariable
            w_association = self.w_method().getliteral(third)
            association = wrapper.AssociationWrapper(self.space, w_association)
            self.push(association.value())
        elif opType == 5:
            self.w_receiver().store(self.space, third, self.top())
        elif opType == 6:
            self.w_receiver().store(self.space, third, self.pop())
        elif opType == 7:
            w_association = self.w_method().getliteral(third)
            association = wrapper.AssociationWrapper(self.space, w_association)
            association.store_value(self.top())

    def singleExtendedSuperBytecode(self, interp):
        selector, argcount = self.getExtendedSelectorArgcount()
        self._sendSuperSelector(selector, argcount, interp)

    def secondExtendedSendBytecode(self, interp):
        descriptor = self.getbytecode()
        selector = self.w_method().getliteralsymbol(descriptor & 63)
        argcount = descriptor >> 6
        self._sendSelfSelector(selector, argcount, interp)

    def popStackBytecode(self, interp):
        self.pop()

    def experimentalBytecode(self, interp):
        raise MissingBytecode("experimentalBytecode")

    def jump(self,offset):
        self.store_pc(self.pc() + offset)

    def jumpConditional(self,bool,position):
        if self.top() == bool:
            self.jump(position)
        self.pop()

    def shortJumpPosition(self):
        return (self.currentBytecode & 7) + 1

    def shortUnconditionalJump(self, interp):
        self.jump(self.shortJumpPosition())

    def shortConditionalJump(self, interp):
        self.jumpConditional(interp.space.w_false, self.shortJumpPosition())

    def longUnconditionalJump(self, interp):
        self.jump((((self.currentBytecode & 7) - 4) << 8) + self.getbytecode())

    def longJumpPosition(self):
        return ((self.currentBytecode & 3) << 8) + self.getbytecode()

    def longJumpIfTrue(self, interp):
        self.jumpConditional(interp.space.w_true, self.longJumpPosition())

    def longJumpIfFalse(self, interp):
        self.jumpConditional(interp.space.w_false, self.longJumpPosition())


    bytecodePrimAdd = make_call_primitive_bytecode(primitives.ADD, "+", 1)
    bytecodePrimSubtract = make_call_primitive_bytecode(primitives.SUBTRACT, "-", 1)
    bytecodePrimLessThan = make_call_primitive_bytecode (primitives.LESSTHAN, "<", 1)
    bytecodePrimGreaterThan = make_call_primitive_bytecode(primitives.GREATERTHAN, ">", 1)
    bytecodePrimLessOrEqual = make_call_primitive_bytecode(primitives.LESSOREQUAL,  "<=", 1)
    bytecodePrimGreaterOrEqual = make_call_primitive_bytecode(primitives.GREATEROREQUAL,  ">=", 1)
    bytecodePrimEqual = make_call_primitive_bytecode(primitives.EQUAL,   "=", 1)
    bytecodePrimNotEqual = make_call_primitive_bytecode(primitives.NOTEQUAL,  "~=", 1)
    bytecodePrimMultiply = make_call_primitive_bytecode(primitives.MULTIPLY,  "*", 1)
    bytecodePrimDivide = make_call_primitive_bytecode(primitives.DIVIDE,  "/", 1)
    bytecodePrimMod = make_call_primitive_bytecode(primitives.MOD, "\\\\", 1)
    bytecodePrimMakePoint = make_call_primitive_bytecode(primitives.MAKE_POINT, "@", 1)
    bytecodePrimBitShift = make_call_primitive_bytecode(primitives.BIT_SHIFT, "bitShift:", 1)
    bytecodePrimDiv = make_call_primitive_bytecode(primitives.DIV, "//", 1)
    bytecodePrimBitAnd = make_call_primitive_bytecode(primitives.BIT_AND, "bitAnd:", 1)
    bytecodePrimBitOr = make_call_primitive_bytecode(primitives.BIT_OR, "bitOr:", 1)

    def bytecodePrimAt(self, interp):
        # n.b.: depending on the type of the receiver, this may invoke
        # primitives.AT, primitives.STRING_AT, or something else for all
        # I know.  
        self._sendSelfSelector("at:", 1, interp)

    def bytecodePrimAtPut(self, interp):
        # n.b. as above
        self._sendSelfSelector("at:put:", 2, interp)

    def bytecodePrimSize(self, interp):
        self._sendSelfSelector("size", 0, interp)

    def bytecodePrimNext(self, interp):
        self._sendSelfSelector("next", 0, interp)

    def bytecodePrimNextPut(self, interp):
        self._sendSelfSelector("nextPut:", 1, interp)

    def bytecodePrimAtEnd(self, interp):
        self._sendSelfSelector("atEnd", 0, interp)

    def bytecodePrimEquivalent(self, interp):
        # short-circuit: classes cannot override the '==' method,
        # which cannot fail
        primitives.prim_table[primitives.EQUIVALENT](interp, 1)

    def bytecodePrimClass(self, interp):
        # short-circuit: classes cannot override the 'class' method,
        # which cannot fail
        primitives.prim_table[primitives.CLASS](interp, 0)


    bytecodePrimBlockCopy = make_call_primitive_bytecode(primitives.BLOCK_COPY, "blockCopy:", 1)
    bytecodePrimValue = make_call_primitive_bytecode(primitives.VALUE, "value", 0)
    bytecodePrimValueWithArg = make_call_primitive_bytecode(primitives.VALUE, "value:", 1)

    def bytecodePrimDo(self, interp):
        self._sendSelfSelector("do:", 1, interp)

    def bytecodePrimNew(self, interp):
        self._sendSelfSelector("new", 0, interp)

    def bytecodePrimNewWithArg(self, interp):
        self._sendSelfSelector("new:", 1, interp)

    def bytecodePrimPointX(self, interp):
        self._sendSelfSelector("x", 0, interp)

    def bytecodePrimPointY(self, interp):
        self._sendSelfSelector("y", 0, interp)


BYTECODE_RANGES = [
            (  0,  15, "pushReceiverVariableBytecode"),
            ( 16,  31, "pushTemporaryVariableBytecode"),
            ( 32,  63, "pushLiteralConstantBytecode"),
            ( 64,  95, "pushLiteralVariableBytecode"),
            ( 96, 103, "storeAndPopReceiverVariableBytecode"),
            (104, 111, "storeAndPopTemporaryVariableBytecode"),
            (112, "pushReceiverBytecode"),
            (113, "pushConstantTrueBytecode"),
            (114, "pushConstantFalseBytecode"),
            (115, "pushConstantNilBytecode"),
            (116, "pushConstantMinusOneBytecode"),
            (117, "pushConstantZeroBytecode"),
            (118, "pushConstantOneBytecode"),
            (119, "pushConstantTwoBytecode"),
            (120, "returnReceiver"),
            (121, "returnTrue"),
            (122, "returnFalse"),
            (123, "returnNil"),
            (124, "returnTopFromMethod"),
            (125, "returnTopFromBlock"),
            (126, "unknownBytecode"),
            (127, "unknownBytecode"),
            (128, "extendedPushBytecode"),
            (129, "extendedStoreBytecode"),
            (130, "extendedStoreAndPopBytecode"),
            (131, "singleExtendedSendBytecode"),
            (132, "doubleExtendedDoAnythingBytecode"),
            (133, "singleExtendedSuperBytecode"),
            (134, "secondExtendedSendBytecode"),
            (135, "popStackBytecode"),
            (136, "duplicateTopBytecode"),
            (137, "pushActiveContextBytecode"),
            (138, 143, "experimentalBytecode"),
            (144, 151, "shortUnconditionalJump"),
            (152, 159, "shortConditionalJump"),
            (160, 167, "longUnconditionalJump"),
            (168, 171, "longJumpIfTrue"),
            (172, 175, "longJumpIfFalse"),
            (176, "bytecodePrimAdd"),
            (177, "bytecodePrimSubtract"),
            (178, "bytecodePrimLessThan"),
            (179, "bytecodePrimGreaterThan"),
            (180, "bytecodePrimLessOrEqual"),
            (181, "bytecodePrimGreaterOrEqual"),
            (182, "bytecodePrimEqual"),
            (183, "bytecodePrimNotEqual"),
            (184, "bytecodePrimMultiply"),
            (185, "bytecodePrimDivide"),
            (186, "bytecodePrimMod"),
            (187, "bytecodePrimMakePoint"),
            (188, "bytecodePrimBitShift"),
            (189, "bytecodePrimDiv"),
            (190, "bytecodePrimBitAnd"),
            (191, "bytecodePrimBitOr"),
            (192, "bytecodePrimAt"),
            (193, "bytecodePrimAtPut"),
            (194, "bytecodePrimSize"),
            (195, "bytecodePrimNext"),
            (196, "bytecodePrimNextPut"),
            (197, "bytecodePrimAtEnd"),
            (198, "bytecodePrimEquivalent"),
            (199, "bytecodePrimClass"),
            (200, "bytecodePrimBlockCopy"),
            (201, "bytecodePrimValue"),
            (202, "bytecodePrimValueWithArg"),
            (203, "bytecodePrimDo"),
            (204, "bytecodePrimNew"),
            (205, "bytecodePrimNewWithArg"),
            (206, "bytecodePrimPointX"),
            (207, "bytecodePrimPointY"),
            (208, 255, "sendLiteralSelectorBytecode"),
            ]


def initialize_bytecode_table():
    result = [None] * 256
    for entry in BYTECODE_RANGES:
        if len(entry) == 2:
            positions = [entry[0]]
        else:
            positions = range(entry[0], entry[1]+1)
        for pos in positions:
            result[pos] = getattr(ContextPartShadow, entry[-1])
    assert None not in result
    return result

BYTECODE_TABLE = initialize_bytecode_table()


def make_bytecode_dispatch_translated():
    # this is a performance optimization: when translating the
    # interpreter, the bytecode dispatching is not implemented as a
    # list lookup and an indirect call but as a switch.

    code = ["def bytecode_dispatch_translated(self, context, bytecode):"]
    prefix = ""
    for entry in BYTECODE_RANGES:
        if len(entry) == 2:
            numbers = [entry[0]]
        else:
            numbers = range(entry[0], entry[1]+1)
        cond = " or ".join(["bytecode == %s" % (i, )
                                for i in numbers])
        code.append("    %sif %s:" % (prefix, cond, ))
        code.append("        context.%s(self)" % (entry[-1], ))
        prefix = "el"
    code.append("bytecode_dispatch_translated._always_inline_ = True")
    source = py.code.Source("\n".join(code))
    print source
    miniglob = {}
    exec source.compile() in miniglob
    return miniglob["bytecode_dispatch_translated"]
    
bytecode_dispatch_translated = make_bytecode_dispatch_translated()
