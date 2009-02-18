'''Toy Language with Cons Cells'''

import autopath
import py
from pypy.rlib.objectmodel import specialize, we_are_translated
from pypy.jit.tl.tlopcode import *
from pypy.jit.tl import tlopcode
from pypy.rlib.jit import hint

class Obj(object):

    def t(self): raise TypeError

    def int_o(self): raise TypeError
    def to_string(self): raise TypeError
    
    def add(self, other): raise TypeError
    def sub(self, other): raise TypeError
    def mul(self, other): raise TypeError
    def div(self, other): raise TypeError
    
    def eq(self, other): raise TypeError
    def lt(self, other): raise TypeError

    def car(self): raise TypeError
    def cdr(self): raise TypeError

    def _concat(self, other): raise TypeError

    # object oriented features
    def getattr(self, name): raise TypeError
    def setattr(self, name, value): raise TypeError
    def send(self, name): raise TypeError # return the bytecode position where the method starts


class ClassDescr(object):

    def __init__(self, attributes, methods):
        self.attributes = attributes
        self.methods = methods

    def __eq__(self, other):
        "NOT_RPYTHON"
        return self.__dict__ == other.__dict__

class ConstantPool(object):

    def __init__(self):
        self.classdescrs = []
        self.strings = []

    def add_classdescr(self, attributes, methods):
        idx = len(self.classdescrs)
        descr = ClassDescr(attributes, methods)
        self.classdescrs.append(descr)
        return idx

    def add_string(self, s):
        try:
            return self.strings.index(s)
        except ValueError:
            idx = len(self.strings)
            self.strings.append(s)
            return idx

    def __eq__(self, other):
        "NOT_RPYTHON"
        return self.__dict__ == other.__dict__

class Class(object):

    classes = [] # [(descr, cls), ...]

    def get(key):
        for descr, cls in Class.classes:
            if key.attributes == descr.attributes and\
               key.methods == descr.methods:
                return cls
        result = Class(key)
        Class.classes.append((key, result))
        return result
    get._pure_function_ = True
    get = staticmethod(get)

    def __init__(self, descr):
        attributes = {} # attrname -> index
        for name in descr.attributes:
            attributes[name] = len(attributes)
        self.attributes = attributes
        self.methods = {}
        for methname, pc in descr.methods:
            self.methods[methname] = pc
    
class InstanceObj(Obj):

    def __init__(self, cls):
        self.cls = cls
        frozenclass = hint(cls, deepfreeze=True)
        self.values = [nil] * len(frozenclass.attributes)

    def getclass(self):
        # promote and deepfreeze the class
        cls = hint(self.cls, promote=True)
        return hint(cls, deepfreeze=True)

    def to_string(self):
        return '<Object>'

    def t(self):
        return True

    def eq(self, other):
        return self is other

    def getattr(self, name):
        i = self.getclass().attributes[name]
        return self.values[i]

    def setattr(self, name, value):
        i = self.getclass().attributes[name]
        self.values[i] = value
        return value

    def send(self, name):
        return self.getclass().methods[name]


class IntObj(Obj):

    def __init__(self, value):
        self.value = value

    def t(self):
        return bool(self.value)

    def int_o(self):
        return self.value

    def to_string(self):
        return str(self.value)

    def add(self, other): return IntObj(self.value + other.int_o())
    def sub(self, other): return IntObj(self.value - other.int_o())
    def mul(self, other): return IntObj(self.value * other.int_o())
    def div(self, other): return IntObj(self.value // other.int_o())

    def eq(self, other):
        return isinstance(other, IntObj) and self.value == other.value

    def lt(self, other): return self.value < other.int_o()

zero = IntObj(0)

class LispObj(Obj):

    def div(self, n):
        n = n.int_o()
        if n < 0:
            raise IndexError
        return self._nth(n)

    def add(self, other):
        if not isinstance(other, LispObj):
            raise TypeError
        return self._concat(other)

class NilObj(LispObj):

    def to_string(self):
        return 'nil'

    def t(self):
        return False

    def eq(self, other):
        return self is other

    def _concat(self, other):
        return other

    def _nth(self, n):
        raise IndexError

nil = NilObj()

class ConsObj(LispObj):
    def __init__(self, car, cdr):
        self._car = car
        self._cdr = cdr

    def to_string(self):
        return '<ConsObj>'

    def t(self):
        return True

    def eq(self, other):
        return (isinstance(other, ConsObj) and
                self._car.eq(other._car) and self._cdr.eq(other._cdr))

    def car(self):
        return self._car

    def cdr(self):
        return self._cdr

    def _concat(self, other):
        return ConsObj(self._car, self._cdr._concat(other))

    def _nth(self, n):
        if n == 0:
            return self._car
        else:
            return self._cdr._nth(n-1)

def char2int(c):
    t = ord(c)
    if t & 128:
        t = -(-ord(c) & 0xff)
    return t

class FrameStack:
    def __init__(self):
        self.pc_stack = []
        self.args_stack = []
        self.stack_stack = []

    def push(self, pc, args, stack):
        self.pc_stack.append(pc)
        self.args_stack.append(args)
        self.stack_stack.append(stack)
        return self

    def pop(self):
        pc = self.pc_stack.pop()
        args = self.args_stack.pop()
        stack = self.stack_stack.pop()
        return pc, args, stack

    def isempty(self):
        return len(self.pc_stack) == 0
        
def make_interp(supports_call, jitted=True):
    if jitted:
        from pypy.rlib.jit import hint
    else:
        @specialize.argtype(0)
        def hint(x, global_merge_point=False,
                 promote_class=False,
                 promote=False,
                 deepfreeze=False,
                 forget=False,
                 concrete=False):
            return x

    def interp(code='', pc=0, inputarg=0, pool=None):
        if not isinstance(code,str):
            raise TypeError("code '%s' should be a string" % str(code))
        
        if pool is None:
            pool = ConstantPool()
        args = [IntObj(inputarg)]
        return interp_eval(code, pc, args, pool).int_o()

    def interp_eval(code, pc, args, pool2):
        code_len = len(code)
        pool = hint(hint(pool2, concrete=True), deepfreeze=True)
        stack = []
        framestack = FrameStack()

        while pc < code_len:
            hint(None, global_merge_point=True)
            opcode = ord(code[pc])
            opcode = hint(opcode, concrete=True)
            pc += 1

            if opcode == NOP:
                pass
            
            elif opcode == NIL:
                stack.append(nil)

            elif opcode == CONS:
                car, cdr = stack.pop(), stack.pop()
                stack.append(ConsObj(car, cdr))

            elif opcode == CAR:
                stack.append(stack.pop().car())

            elif opcode == CDR:
                stack.append(stack.pop().cdr())
                
            elif opcode == PUSH:
                stack.append(IntObj(char2int(code[pc])))
                pc += 1

            elif opcode == POP:
                stack.pop()

            elif opcode == SWAP:
                a, b = stack.pop(), stack.pop()
                stack.append(a)
                stack.append(b)

            elif opcode == ROLL: #rotate stack top to somewhere below
                r = char2int(code[pc])
                if r < -1:
                    i = len(stack) + r
                    if i < 0:
                        raise IndexError
                    stack.insert( i, stack.pop() )
                elif r > 1:
                    i = len(stack) - r
                    if i < 0:
                        raise IndexError
                    stack.append(stack.pop(i))

                pc += 1

            elif opcode == PICK:
                stack.append( stack[-1 - char2int(code[pc])] )
                pc += 1

            elif opcode == PUT:
                stack[-1 - char2int(code[pc])] = stack.pop()
                pc += 1

            elif opcode == ADD:
                a, b = stack.pop(), stack.pop()
                hint(a, promote_class=True)
                hint(b, promote_class=True)
                stack.append(b.add(a))

            elif opcode == SUB:
                a, b = stack.pop(), stack.pop()
                hint(a, promote_class=True)
                hint(b, promote_class=True)
                stack.append(b.sub(a))

            elif opcode == MUL:
                a, b = stack.pop(), stack.pop()
                hint(a, promote_class=True)
                hint(b, promote_class=True)
                stack.append(b.mul(a))

            elif opcode == DIV:
                a, b = stack.pop(), stack.pop()
                hint(a, promote_class=True)
                hint(b, promote_class=True)
                stack.append(b.div(a))

            elif opcode == EQ:
                a, b = stack.pop(), stack.pop()
                hint(a, promote_class=True)
                hint(b, promote_class=True)
                stack.append(IntObj(b.eq(a)))

            elif opcode == NE:
                a, b = stack.pop(), stack.pop()
                hint(a, promote_class=True)
                hint(b, promote_class=True)
                stack.append(IntObj(not b.eq(a)))

            elif opcode == LT:
                a, b = stack.pop(), stack.pop()
                hint(a, promote_class=True)
                hint(b, promote_class=True)
                stack.append(IntObj(b.lt(a)))

            elif opcode == LE:
                a, b = stack.pop(), stack.pop()
                hint(a, promote_class=True)
                hint(b, promote_class=True)
                stack.append(IntObj(not a.lt(b)))

            elif opcode == GT:
                a, b = stack.pop(), stack.pop()
                hint(a, promote_class=True)
                hint(b, promote_class=True)
                stack.append(IntObj(a.lt(b)))

            elif opcode == GE:
                a, b = stack.pop(), stack.pop()
                hint(a, promote_class=True)
                hint(b, promote_class=True)
                stack.append(IntObj(not b.lt(a)))

            elif opcode == BR:
                pc += char2int(code[pc])
                pc += 1
                
            elif opcode == BR_COND:
                cond = stack.pop()
                hint(cond, promote_class=True)
                if cond.t():
                    pc += char2int(code[pc])
                pc += 1

            elif opcode == BR_COND_STK:
                offset = stack.pop().int_o()
                if stack.pop().t():
                    pc += hint(offset, forget=True)

            elif supports_call and opcode == CALL:
                offset = char2int(code[pc])
                pc += 1
                framestack.push(pc, args, stack)
                pc = pc + offset
                args = [zero]
                stack = []

            elif opcode == RETURN:
                if framestack.isempty():                    
                    break
                if stack:
                    res = stack.pop()
                else:
                    res = None
                pc2, args, stack = framestack.pop()
                pc = hint(pc2, promote=True)
                if res:
                    stack.append(res)

            elif opcode == PUSHARG:
                stack.append(args[0])

            elif opcode == PUSHARGN:
                idx = char2int(code[pc])
                pc += 1
                stack.append(args[idx])

            elif opcode == NEW:
                idx = char2int(code[pc])
                pc += 1
                descr = pool.classdescrs[idx]
                cls = Class.get(descr)
                stack.append(InstanceObj(cls))

            elif opcode == GETATTR:
                idx = char2int(code[pc])
                pc += 1
                name = pool.strings[idx]
                a = stack.pop()
                hint(a, promote_class=True)
                stack.append(a.getattr(name))

            elif opcode == SETATTR:
                idx = char2int(code[pc])
                pc += 1
                name = pool.strings[idx]
                a, b = stack.pop(), stack.pop()
                hint(a, promote_class=True)
                hint(b, promote_class=True)
                b.setattr(name, a)

            elif supports_call and opcode == SEND:
                idx = char2int(code[pc])
                pc += 1
                num_args = char2int(code[pc])
                pc += 1
                num_args += 1 # include self
                name = pool.strings[idx]
                meth_args = [None] * num_args
                while num_args > 0:
                    num_args -= 1
                    meth_args[num_args] = stack.pop()
                    hint(num_args, concrete=True)
                a = meth_args[0]
                # XXX: if you uncomment the next line,
                # test_0tlc.test_expr fails
                hint(a, promote_class=True)

                meth_pc = hint(a.send(name), promote=True)
                framestack.push(pc, args, stack)
                pc = meth_pc
                args = meth_args
                stack = []

            elif supports_call and opcode == CALLARGS:
                offset = char2int(code[pc])
                pc += 1
                num_args = char2int(code[pc])
                pc += 1
                call_args = [None] * num_args
                while num_args > 0:
                    num_args -= 1
                    call_args[num_args] = stack.pop()
                    hint(num_args, concrete=True)
                framestack.push(pc, args, stack)
                pc = pc + offset - 1
                args = call_args
                stack = []

            elif opcode == PRINT:
                if not we_are_translated():
                    a = stack.pop()
                    hint(a, promote_class=True)
                    print a.to_string()

            elif opcode == DUMP:
                if not we_are_translated():
                    parts = []
                    for obj in stack:
                        hint(obj, promote_class=True)
                        parts.append(obj.to_string())
                    print '[%s]' % ', '.join(parts)

            else:
                raise RuntimeError("unknown opcode: " + str(opcode))

        return stack[-1]
    
    return interp, interp_eval


interp             , interp_eval               = make_interp(supports_call = True)
interp_without_call, interp_eval_without_call  = make_interp(supports_call = False)
interp_nonjit      , interp_eval_nonjit        = make_interp(supports_call = True, jitted=False)

if __name__ == '__main__':
    import sys
    from pypy.jit.tl.test.test_tl import FACTORIAL_SOURCE
    if len(sys.argv) == 1:
        src = FACTORIAL_SOURCE
    elif len(sys.argv) == 2:
        src = file(sys.argv[1]).read()
    else:
        print >> sys.stderr, 'Usage: python tlc.py [sourcefile]'
        sys.exit(2)

    pool = ConstantPool()
    bytecode = compile(src, pool)
    sys.stdout.write(serialize_program(bytecode, pool))
