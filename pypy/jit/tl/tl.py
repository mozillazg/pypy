'''Toy Language'''

import py
from pypy.jit.tl.tlopcode import *
from pypy.rlib.jit import JitDriver

def char2int(c):
    t = ord(c)
    if t & 128:
        t = -(-ord(c) & 0xff)
    return t

class Stack(object):
    def __init__(self, size):
        self.stack = [0] * size
        self.stackpos = 0

    def append(self, elem):
        self.stack[self.stackpos] = elem
        self.stackpos += 1

    def pop(self):
        self.stackpos -= 1
        if self.stackpos < 0:
            raise IndexError
        return self.stack[self.stackpos]

def make_interp(supports_call):
    myjitdriver = JitDriver(greens = ['pc', 'code'],
                            reds = ['stack', 'inputarg'])
    def interp(code='', pc=0, inputarg=0):
        if not isinstance(code,str):
            raise TypeError("code '%s' should be a string" % str(code))

        stack = Stack(len(code))

        while pc < len(code):
            myjitdriver.jit_merge_point(pc=pc, code=code,
                                        stack=stack, inputarg=inputarg)
            opcode = ord(code[pc])
            pc += 1

            if opcode == NOP:
                pass

            elif opcode == PUSH:
                stack.append( char2int(code[pc]) )
                pc += 1

            elif opcode == POP:
                stack.pop()

            elif opcode == SWAP:
                a, b = stack.pop(), stack.pop()
                stack.append(a)
                stack.append(b)

            elif opcode == ROLL: #rotate stack top to somewhere below
                raise NotImplementedError("ROLL")
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
                    stack.roll(i)

                pc += 1

            elif opcode == PICK:
                raise NotImplementedError("PICK")
                stack.append( stack[-1 - char2int(code[pc])] )
                pc += 1

            elif opcode == PUT:
                raise NotImplementedError("PUT")
                stack[-1 - char2int(code[pc])] = stack.pop()
                pc += 1

            elif opcode == ADD:
                a, b = stack.pop(), stack.pop()
                stack.append( b + a )

            elif opcode == SUB:
                a, b = stack.pop(), stack.pop()
                stack.append( b - a )

            elif opcode == MUL:
                a, b = stack.pop(), stack.pop()
                stack.append( b * a )

            elif opcode == DIV:
                a, b = stack.pop(), stack.pop()
                stack.append( b / a )

            elif opcode == EQ:
                a, b = stack.pop(), stack.pop()
                stack.append( b == a )

            elif opcode == NE:
                a, b = stack.pop(), stack.pop()
                stack.append( b != a )

            elif opcode == LT:
                a, b = stack.pop(), stack.pop()
                stack.append( b <  a )

            elif opcode == LE:
                a, b = stack.pop(), stack.pop()
                stack.append( b <= a )

            elif opcode == GT:
                a, b = stack.pop(), stack.pop()
                stack.append( b >  a )

            elif opcode == GE:
                a, b = stack.pop(), stack.pop()
                stack.append( b >= a )

            elif opcode == BR_COND:
                if stack.pop():
                    pc += char2int(code[pc]) + 1
                    myjitdriver.can_enter_jit(pc=pc, code=code,
                                              stack=stack, inputarg=inputarg)
                else:
                    pc += 1

            elif opcode == BR_COND_STK:
                offset = stack.pop()
                if stack.pop():
                    pc += offset
                    myjitdriver.can_enter_jit(pc=pc, code=code,
                                              stack=stack, inputarg=inputarg)

            elif supports_call and opcode == CALL:
                offset = char2int(code[pc])
                pc += 1
                res = interp(code, pc + offset)
                stack.append( res )

            elif opcode == RETURN:
                break

            elif opcode == PUSHARG:
                stack.append( inputarg )

            else:
                raise RuntimeError("unknown opcode: " + str(opcode))

        return stack.pop()

    return interp


interp              = make_interp(supports_call = True)
interp_without_call = make_interp(supports_call = False)
