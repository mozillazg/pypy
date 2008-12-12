'''Toy Language with Cons Cells'''

import autopath
import py
from pypy.rlib.objectmodel import specialize
from pypy.jit.tl.tlopcode import *
from pypy.jit.tl import tlopcode
from pypy.rlib.jit import hint

class Obj(object):

    def t(self): raise TypeError

    def int_o(self): raise TypeError
    
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


class ClassDescr(object):

    def __init__(self, attributes, methods):
        self.attributes = attributes
        self.methods = methods

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

class Class(object):

    classes = [] # [(attributes, cls), ...]

    def get(key):
        for attributes, cls in Class.classes:
            if attributes == key:
                return cls
        result = Class(key)
        Class.classes.append((key, result))
        return result
    get._pure_function_ = True
    get = staticmethod(get)

    def __init__(self, attrlist):
        attributes = {} # attrname -> index
        for name in attrlist:
            attributes[name] = len(attributes)
        self.attributes = attributes
    
class InstanceObj(Obj):

    def __init__(self, cls):
        self.cls = cls
        frozenclass = hint(cls, deepfreeze=True)
        self.values = [nil] * len(frozenclass.attributes)

    def getclass(self):
        # promote and deepfreeze the class
        cls = hint(self.cls, promote=True)
        return hint(cls, deepfreeze=True)

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

class IntObj(Obj):

    def __init__(self, value):
        self.value = value

    def t(self):
        return bool(self.value)

    def int_o(self):
        return self.value

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
        return interp_eval(code, pc, IntObj(inputarg), pool).int_o()

    def interp_eval(code, pc, inputarg, pool2):
        code_len = len(code)
        stack = []
        pool = hint(hint(pool2, concrete=True), deepfreeze=True)

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
                res = interp_eval(code, pc + offset, zero, pool2)
                stack.append( res )

            elif opcode == RETURN:
                break

            elif opcode == PUSHARG:
                stack.append(inputarg)

            elif opcode == NEW:
                idx = char2int(code[pc])
                pc += 1
                descr = pool.classdescrs[idx]
                cls = Class.get(descr.attributes)
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
    print serialize_pool(pool)
    print bytecode
