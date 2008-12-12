names = {}

def opcode(n, opcode_name):
    global opcode_names
    names[opcode_name] = globals()[opcode_name] = n

# basic tl opcodes: 

opcode(1,  "NOP")
opcode(2,  "PUSH")     #1 operand
opcode(3,  "POP")
opcode(4,  "SWAP")
opcode(5,  "ROLL")

opcode(6,  "PICK")     #1 operand (DUP = PICK,0)
opcode(7,  "PUT")      #1 operand

opcode(8,  "ADD")
opcode(9,  "SUB")
opcode(10, "MUL")
opcode(11, "DIV")

opcode(12, "EQ")
opcode(13, "NE")
opcode(14, "LT")
opcode(15, "LE")
opcode(16, "GT")
opcode(17, "GE")

opcode(18, "BR_COND")  #1 operand offset
opcode(19, "BR_COND_STK")    # no operand, takes [condition, offset] from the stack

opcode(20, "CALL")  #1 operand offset
opcode(21, "RETURN")

opcode(22, "PUSHARG")

opcode(23, "INVALID")

# tl with cons cells  and boxed values opcodes

opcode(24, "NIL")
opcode(25, "CONS")
opcode(26, "CAR")
opcode(27, "CDR")

# object oriented features of tlc
opcode(28, "NEW")
opcode(29, "GETATTR")
opcode(30, "SETATTR")
opcode(31, "SEND")

del opcode


def compile(code='', pool=None):
    bytecode = []
    labels   = {}        #[key] = pc
    label_usage = []     #(name, pc)
    method_usage = []    #[methods]
    for s in code.split('\n'):
        for comment in '; # //'.split():
            s = s.split(comment, 1)[0]
        s = s.strip()
        if not s:
            continue
        t = s.split()
        if t[0].endswith(':'):
            assert ',' not in t[0]
            labels[ t[0][:-1] ] = len(bytecode)
            continue
        bytecode.append(names[t[0]])
        if len(t) > 1:
            arg = t[1]
            try:
                bytecode.append( int(arg) )
            except ValueError:
                if t[0] == 'NEW':
                    # it's a class descr
                    items = arg.split(',')
                    items = [x.strip() for x in items if x]
                    attributes = []
                    methods = []
                    for item in items:
                        if '=' in item:
                            methname, label = item.split('=')
                            methods.append((methname, label))
                        else:
                            attributes.append(item)
                    assert pool is not None
                    idx = pool.add_classdescr(attributes, methods)
                    method_usage.append(methods)
                    bytecode.append(idx)
                elif t[0] in ('GETATTR', 'SETATTR', 'SEND'):
                    # it's a string
                    idx = pool.add_string(arg)
                    bytecode.append(idx)
                else:
                    # it's a label
                    label_usage.append( (arg, len(bytecode)) )
                    bytecode.append( 0 )
    for label, pc in label_usage:
        bytecode[pc] = labels[label] - pc - 1
    for methods in method_usage:
        for i, (methname, label) in enumerate(methods):
            pc = labels[label]
            methods[i] = (methname, pc)
    return ''.join([chr(i & 0xff) for i in bytecode])  

def serialize_pool(pool):
    lists = [','.join(lst) for lst in pool.strlists]
    return '|'.join(lists)
