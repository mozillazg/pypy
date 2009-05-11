
import math
from pypy.lang.js.jsparser import parse, ParseError
from pypy.lang.js.astbuilder import ASTBuilder
from pypy.lang.js.jsobj import global_context, W_Object,\
     w_Undefined, W_NewBuiltin, W_IntNumber, w_Null, create_object, W_Boolean,\
     W_FloatNumber, W_String, W_Builtin, W_Array, w_Null, newbool,\
     isnull_or_undefined, W_PrimitiveObject, W_ListObject, W_BaseNumber,\
     DE, DD, RO, IT
from pypy.lang.js.execution import ThrowException, JsTypeError
from pypy.rlib.objectmodel import we_are_translated
from pypy.rlib.streamio import open_file_as_stream
from pypy.lang.js.jscode import JsCode
from pypy.rlib.rarithmetic import NAN, INFINITY, isnan, isinf, r_uint
from pypy.rlib.objectmodel import specialize
from pypy.rlib.listsort import TimSort

ASTBUILDER = ASTBuilder()

def writer(x):
    print x

def load_source(script_source, sourcename):
    temp_tree = parse(script_source)
    ASTBUILDER.sourcename = sourcename
    return ASTBUILDER.dispatch(temp_tree)

def load_file(filename):
    f = open_file_as_stream(filename)
    t = load_source(f.readall(), filename)
    f.close()
    return t

class W_NativeObject(W_Object):
    def __init__(self, Class, Prototype, ctx=None,
                 Value=w_Undefined, callfunc=None):
        W_Object.__init__(self, ctx, Prototype,
                          Class, Value, callfunc)
    
class W_ObjectObject(W_NativeObject):
    def Call(self, ctx, args=[], this=None):
        if len(args) >= 1 and not isnull_or_undefined(args[0]):
            return args[0].ToObject(ctx)
        else:
            return self.Construct(ctx)

    def Construct(self, ctx, args=[]):
        if (len(args) >= 1 and not args[0] is w_Undefined and not
            args[0] is w_Null):
            # XXX later we could separate builtins and normal objects
            return args[0].ToObject(ctx)
        return create_object(ctx, 'Object')

class W_BooleanObject(W_NativeObject):
    def Call(self, ctx, args=[], this=None):
        if len(args) >= 1 and not isnull_or_undefined(args[0]):
            return newbool(args[0].ToBoolean())
        else:
            return newbool(False)

    def Construct(self, ctx, args=[]):
        if len(args) >= 1 and not isnull_or_undefined(args[0]):
            Value = newbool(args[0].ToBoolean())
            return create_object(ctx, 'Boolean', Value = Value)
        return create_object(ctx, 'Boolean', Value = newbool(False))

class W_NumberObject(W_NativeObject):
    def Call(self, ctx, args=[], this=None):
        if len(args) >= 1 and not isnull_or_undefined(args[0]):
            return W_FloatNumber(args[0].ToNumber(ctx))
        elif len(args) >= 1 and args[0] is w_Undefined:
            return W_FloatNumber(NAN)
        else:
            return W_FloatNumber(0.0)

    def ToNumber(self, ctx):
        return 0.0

    def Construct(self, ctx, args=[]):
        if len(args) >= 1 and not isnull_or_undefined(args[0]):
            Value = W_FloatNumber(args[0].ToNumber(ctx))
            return create_object(ctx, 'Number', Value = Value)
        return create_object(ctx, 'Number', Value = W_FloatNumber(0.0))

class W_StringObject(W_NativeObject):
    length = 1
    def Call(self, ctx, args=[], this=None):
        if len(args) >= 1:
            return W_String(args[0].ToString(ctx))
        else:
            return W_String('')

    def Construct(self, ctx, args=[]):
        if len(args) >= 1:
            Value = W_String(args[0].ToString(ctx))
        else:
            Value = W_String('')
        return Value.ToObject(ctx)

def create_array(ctx, elements=[]):
    proto = ctx.get_global().Get(ctx, 'Array').Get(ctx, 'prototype')
    array = W_Array(ctx, Prototype=proto, Class = proto.Class)
    i = 0
    while i < len(elements):
        array.Put(ctx, str(i), elements[i])
        i += 1
    
    return array

class W_ArrayObject(W_NativeObject):
    def Call(self, ctx, args=[], this=None):
        if len(args) == 1 and isinstance(args[0], W_BaseNumber):
            array = create_array(ctx)
            array.Put(ctx, 'length', args[0])
        else:
            array = create_array(ctx, args)
        return array

    def Construct(self, ctx, args=[]):
        return self.Call(ctx, args)

TEST = False

class W_Eval(W_NewBuiltin):
    length = 1
    def Call(self, ctx, args=[], this=None):
        if len(args) >= 1:
            if  isinstance(args[0], W_String):
                src = args[0].strval
            else:
                return args[0]
        else:
            return w_Undefined
        
        try:
            node = load_source(src, 'evalcode')
        except ParseError, e:
            raise ThrowException(W_String('SyntaxError: '+str(e)))

        bytecode = JsCode()
        node.emit(bytecode)
        return bytecode.run(ctx, retlast=True)

class W_ParseInt(W_NewBuiltin):
    length = 1
    def Call(self, ctx, args=[], this=None):
        if len(args) < 1:
            return W_FloatNumber(NAN)
        s = args[0].ToString(ctx).strip(" ")
        if len(args) > 1:
            radix = args[1].ToInt32(ctx)
        else:
            radix = 10
        if len(s) >= 2 and (s.startswith('0x') or s.startswith('0X')) :
            radix = 16
            s = s[2:]
        if s == '' or radix < 2 or radix > 36:
            return W_FloatNumber(NAN)
        try:
            n = int(s, radix)
        except ValueError:
            return W_FloatNumber(NAN)
        return W_IntNumber(n)

class W_ParseFloat(W_NewBuiltin):
    length = 1
    def Call(self, ctx, args=[], this=None):
        if len(args) < 1:
            return W_FloatNumber(NAN)
        s = args[0].ToString(ctx).strip(" ")
        try:
            n = float(s)
        except ValueError:
            n = NAN
        return W_FloatNumber(n)

def printjs(ctx, args, this):
    writer(",".join([i.ToString(ctx) for i in args]))
    return w_Undefined

def isnanjs(ctx, args, this):
    if len(args) < 1:
        return newbool(True)
    return newbool(isnan(args[0].ToNumber(ctx)))

def isfinitejs(ctx, args, this):
    if len(args) < 1:
        return newbool(True)
    n = args[0].ToNumber(ctx)
    if  isinf(n) or isnan(n):
        return newbool(False)
    else:
        return newbool(True)
        
def absjs(ctx, args, this):
    val = args[0]
    if isinstance(val, W_IntNumber):
        if val.intval > 0:
            return val # fast path
        return W_IntNumber(-val.intval)
    return W_FloatNumber(abs(args[0].ToNumber(ctx)))

def floorjs(ctx, args, this):
    return W_IntNumber(int(math.floor(args[0].ToNumber(ctx))))

def powjs(ctx, args, this):
    return W_FloatNumber(math.pow(args[0].ToNumber(ctx), args[1].ToNumber(ctx)))

def sqrtjs(ctx, args, this):
    return W_FloatNumber(math.sqrt(args[0].ToNumber(ctx)))

def versionjs(ctx, args, this):
    return w_Undefined

def _ishex(ch):
    return ((ch >= 'a' and ch <= 'f') or (ch >= '0' and ch <= '9') or
            (ch >= 'A' and ch <= 'F'))

def unescapejs(ctx, args, this):
    # XXX consider using StringBuilder here
    res = []
    if not isinstance(args[0], W_String):
        raise JsTypeError(W_String("Expected string"))
    strval = args[0].strval
    lgt = len(strval)
    i = 0
    while i < lgt:
        ch = strval[i]
        if ch == '%':
            if (i + 2 < lgt and _ishex(strval[i+1]) and _ishex(strval[i+2])):
                ch = chr(int(strval[i + 1] + strval[i + 2], 16))
                i += 2
            elif (i + 5 < lgt and strval[i + 1] == 'u' and
                  _ishex(strval[i + 2]) and _ishex(strval[i + 3]) and
                  _ishex(strval[i + 4]) and _ishex(strval[i + 5])):
                ch = chr(int(strval[i+2:i+6], 16))
                i += 5
        i += 1
        res.append(ch)
    return W_String(''.join(res))

class W_ToString(W_NewBuiltin):
    def Call(self, ctx, args=[], this=None):
        return W_String("[object %s]"%this.Class)

class W_ValueOf(W_NewBuiltin):
    length = 0
    def Call(self, ctx, args=[], this=None):
        return this

class W_HasOwnProperty(W_NewBuiltin):
    def Call(self, ctx, args=[], this=None):
        if len(args) >= 1:
            propname = args[0].ToString(ctx)
            if propname in this.propdict:
                return newbool(True)
        return newbool(False)

class W_IsPrototypeOf(W_NewBuiltin):
    def Call(self, ctx, args=[], this=None):
        if len(args) >= 1 and isinstance(args[0], W_PrimitiveObject):
            O = this
            V = args[0].Prototype
            while V is not None:
                if O == V:
                    return newbool(True)
                V = V.Prototype
        return newbool(False)

class W_PropertyIsEnumerable(W_NewBuiltin):
    def Call(self, ctx, args=[], this=None):
        if len(args) >= 1:
            propname = args[0].ToString(ctx)
            if propname in this.propdict and not this.propdict[propname].flags & DE:
                return newbool(True)
        return newbool(False)

class W_Function(W_NewBuiltin):
    def Call(self, ctx, args=[], this=None):
        tam = len(args)
        if tam >= 1:
            fbody  = args[tam-1].ToString(ctx)
            argslist = []
            for i in range(tam-1):
                argslist.append(args[i].ToString(ctx))
            fargs = ','.join(argslist)
            functioncode = "function (%s) {%s}"%(fargs, fbody)
        else:
            functioncode = "function () {}"
        #remove program and sourcelements node
        funcnode = parse(functioncode).children[0].children[0]
        ast = ASTBUILDER.dispatch(funcnode)
        bytecode = JsCode()
        ast.emit(bytecode)
        return bytecode.run(ctx, retlast=True)
    
    def Construct(self, ctx, args=[]):
        return self.Call(ctx, args, this=None)

functionstring= 'function (arguments go here!) {\n'+ \
                '    [lots of stuff :)]\n'+ \
                '}'
class W_FToString(W_NewBuiltin):
    def Call(self, ctx, args=[], this=None):
        if this.Class == 'Function':
            return W_String(functionstring)
        else:
            raise JsTypeError('this is not a function object')

class W_Apply(W_NewBuiltin):
    def Call(self, ctx, args=[], this=None):
        try:
            if isnull_or_undefined(args[0]):
                thisArg = ctx.get_global()
            else:
                thisArg = args[0].ToObject(ctx)
        except IndexError:
            thisArg = ctx.get_global()
        
        try:
            arrayArgs = args[1]
            if isinstance(arrayArgs, W_ListObject):
                callargs = arrayArgs.tolist()
            elif isnull_or_undefined(arrayArgs):
                callargs = []
            else:
                raise JsTypeError('arrayArgs is not an Array or Arguments object')
        except IndexError:
            callargs = []
        return this.Call(ctx, callargs, this=thisArg)

class W_Call(W_NewBuiltin):
    def Call(self, ctx, args=[], this=None):
        if len(args) >= 1:
            if isnull_or_undefined(args[0]):
                thisArg = ctx.get_global()
            else:
                thisArg = args[0]
            callargs = args[1:]
        else:
            thisArg = ctx.get_global()
            callargs = []
        return this.Call(ctx, callargs, this = thisArg)

class W_ValueToString(W_NewBuiltin):
    "this is the toString function for objects with Value"
    mytype = ''
    def Call(self, ctx, args=[], this=None):
        if this.Value.type() != self.mytype:
            raise JsTypeError('Wrong type')
        return W_String(this.Value.ToString(ctx))


class W_NumberValueToString(W_ValueToString):
    mytype = 'number'

class W_BooleanValueToString(W_ValueToString):
    mytype = 'boolean'

class W_StringValueToString(W_ValueToString):
    mytype = 'string'


@specialize.memo()
def get_value_of(type):
    class W_ValueValueOf(W_NewBuiltin):
        "this is the valueOf function for objects with Value"
        def Call(self, ctx, args=[], this=None):
            if type != this.Class:
                raise JsTypeError('%s.prototype.valueOf called with incompatible type' % self.type())
            return this.Value
    return W_ValueValueOf

class W_FromCharCode(W_NewBuiltin):
    length = 1
    def Call(self, ctx, args=[], this=None):
        temp = []
        for arg in args:
            i = arg.ToInt32(ctx) % 65536 # XXX should be uint16
            temp.append(chr(i))
        return W_String(''.join(temp))

class W_CharAt(W_NewBuiltin):
    length = 1
    def Call(self, ctx, args=[], this=None):
        string = this.ToString(ctx)
        if len(args)>=1:
            pos = args[0].ToInt32(ctx)
            if (not pos >=0) or (pos > len(string) - 1):
                return W_String('')
        else:
            return W_String('')
        return W_String(string[pos])

class W_CharCodeAt(W_NewBuiltin):
    def Call(self, ctx, args=[], this=None):
        string = this.ToString(ctx)
        if len(args)>=1:
            pos = args[0].ToInt32(ctx)
            if pos < 0 or pos > len(string) - 1:
                return W_FloatNumber(NAN)
        else:
            return W_FloatNumber(NAN)
        char = string[pos]
        return W_IntNumber(ord(char))

class W_Concat(W_NewBuiltin):
    def Call(self, ctx, args=[], this=None):
        string = this.ToString(ctx)
        others = [obj.ToString(ctx) for obj in args]
        string += ''.join(others)
        return W_String(string)

class W_IndexOf(W_NewBuiltin):
    length = 1
    def Call(self, ctx, args=[], this=None):
        string = this.ToString(ctx)
        if len(args) < 1:
            return W_IntNumber(-1)
        substr = args[0].ToString(ctx)
        size = len(string)
        subsize = len(substr)
        if len(args) < 2:
            pos = 0
        else:
            pos = args[1].ToInteger(ctx)
        pos = int(min(max(pos, 0), size))
        assert pos >= 0
        return W_IntNumber(string.find(substr, pos))

class W_LastIndexOf(W_NewBuiltin):
    length = 1
    def Call(self, ctx, args=[], this=None):
        string = this.ToString(ctx)
        if len(args) < 1:
            return W_IntNumber(-1)
        substr = args[0].ToString(ctx)
        if len(args) < 2:
            pos = INFINITY
        else:
            val = args[1].ToNumber(ctx)
            if isnan(val):
                pos = INFINITY
            else:
                pos = args[1].ToInteger(ctx)
        size = len(string)
        pos = int(min(max(pos, 0), size))
        subsize = len(substr)
        endpos = pos+subsize
        assert endpos >= 0
        return W_IntNumber(string.rfind(substr, 0, endpos))

class W_Substring(W_NewBuiltin):
    length = 2
    def Call(self, ctx, args=[], this=None):
        string = this.ToString(ctx)
        size = len(string)
        if len(args) < 1:
            start = 0
        else:
            start = args[0].ToInteger(ctx)
        if len(args) < 2:
            end = size
        else:
            end = args[1].ToInteger(ctx)
        tmp1 = min(max(start, 0), size)
        tmp2 = min(max(end, 0), size)
        start = min(tmp1, tmp2)
        end = max(tmp1, tmp2)
        return W_String(string[start:end])

class W_Split(W_NewBuiltin):
    length = 2
    def Call(self, ctx, args=[], this=None):
        string = this.ToString(ctx)
        
        if len(args) < 1 or args[0] is w_Undefined:
            return create_array(ctx, [W_String(string)])
        else:
            separator = args[0].ToString(ctx)
        
        if len(args) >= 2:
            limit = args[1].ToUInt32(ctx)
            raise ThrowException(W_String("limit not implemented"))
            # array = string.split(separator, limit)
        else:
            array = string.split(separator)
        
        w_array = create_array(ctx)
        i = 0
        while i < len(array):
            w_str = W_String(array[i])
            w_array.Put(ctx, str(i), w_str)
            i += 1
        
        return w_array

class W_ToLowerCase(W_NewBuiltin):
    length = 0
    def Call(self, ctx, args=[], this=None):
        string = this.ToString(ctx)
        return W_String(string.lower())

class W_ToUpperCase(W_NewBuiltin):
    length = 0
    def Call(self, ctx, args=[], this=None):
        string = this.ToString(ctx)
        return W_String(string.upper())

def common_join(ctx, this, sep=','):
    length = this.Get(ctx, 'length').ToUInt32(ctx)
    l = []
    i = 0
    while i < length:
        item = this.Get(ctx, str(i))
        if isnull_or_undefined(item):
            item_string = ''
        else:
            item_string = item.ToString(ctx)
        l.append(item_string)
        i += 1
        
    return sep.join(l)

class W_ArrayToString(W_NewBuiltin):
    length = 0
    def Call(self, ctx, args=[], this=None):
        return W_String(common_join(ctx, this, sep=','))

class W_ArrayJoin(W_NewBuiltin):
    length = 1
    def Call(self, ctx, args=[], this=None):
        if len(args) >= 1 and not args[0] is w_Undefined:
            sep = args[0].ToString(ctx)
        else:
            sep = ','
        
        return W_String(common_join(ctx, this, sep))

class W_ArrayReverse(W_NewBuiltin):
    length = 0
    def Call(self, ctx, args=[], this=None):
        r2 = this.Get(ctx, 'length').ToUInt32(ctx)
        k = r_uint(0)
        r3 = r_uint(math.floor( float(r2)/2.0 ))
        if r3 == k:
            return this
        
        while k < r3:
            r6 = r2 - k - 1
            r7 = str(k)
            r8 = str(r6)
            
            r9 = this.Get(ctx, r7)
            r10 = this.Get(ctx, r8)
            
            this.Put(ctx, r7, r10)
            this.Put(ctx, r8, r9)
            k += 1
        
        return this

class Sorter(TimSort):
    def __init__(self, list, listlength=None, compare_fn=None, ctx=None):
        TimSort.__init__(self, list, listlength)
        self.compare_fn = compare_fn
        self.ctx = ctx
    
    def lt(self, a, b):
        if self.compare_fn:
            result = self.compare_fn.Call(self.ctx, [a, b]).ToInt32(self.ctx)
            return result == -1
        return a.ToString(self.ctx) < b.ToString(self.ctx)

class W_ArraySort(W_NewBuiltin):
    length = 1
    #XXX: further optimize this function
    def Call(self, ctx, args=[], this=None):
        length = this.Get(ctx, 'length').ToUInt32(ctx)
        
        # According to ECMA-262 15.4.4.11, non-existing properties always come after
        # existing values. Undefined is always greater than any other value.
        # So we create a list of non-undefined values, sort them, and append undefined again.
        values = []
        undefs = r_uint(0)
        
        for i in range(length):
            P = str(i)
            if not this.HasProperty(P):
                # non existing property
                continue
            obj = this.Get(ctx, str(i))
            if obj is w_Undefined:
                undefs += 1
                continue
            values.append(obj)
        
        # sort all values
        if len(args) > 0 and args[0] is not w_Undefined:
            sorter = Sorter(values, compare_fn=args[0], ctx=ctx)
        else:
            sorter = Sorter(values, ctx=ctx)
        sorter.sort()
        
        # put sorted values back
        values = sorter.list
        for i in range(len(values)):
            this.Put(ctx, str(i), values[i])
        
        # append undefined values
        newlength = len(values)
        while undefs > 0:
            undefs -= 1
            this.Put(ctx, str(newlength), w_Undefined)
            newlength += 1
        
        # delete non-existing elements on the end
        while length > newlength:
            this.Delete(str(newlength))
            newlength += 1
        return this

class W_DateFake(W_NewBuiltin): # XXX This is temporary
    def Call(self, ctx, args=[], this=None):
        return create_object(ctx, 'Object')
    
    def Construct(self, ctx, args=[]):
        return create_object(ctx, 'Object')

def pypy_repr(ctx, repr, w_arg):
    return W_String(w_arg.__class__.__name__)

def put_values(ctx, obj, dictvalues):
    for key,value in dictvalues.iteritems():
        obj.Put(ctx, key, value)

class Interpreter(object):
    """Creates a js interpreter"""
    def __init__(self):        
        allon = DE | DD | RO
        w_Global = W_Object(Class="global")
        
        ctx = global_context(w_Global)
        
        w_ObjPrototype = W_Object(Prototype=None, Class='Object')
        
        w_Function = W_Function(ctx, Class='Function', 
                              Prototype=w_ObjPrototype)
        w_FncPrototype = W_Function(ctx, Class='Function', Prototype=w_ObjPrototype)#W_Object(Prototype=None, Class='Function')
        
        w_Function.Put(ctx, 'length', W_IntNumber(1), flags = allon)
        w_Global.Put(ctx, 'Function', w_Function)
        
        w_Object = W_ObjectObject('Object', w_FncPrototype)
        w_Object.Put(ctx, 'prototype', w_ObjPrototype, flags = allon)
        w_Object.Put(ctx, 'length', W_IntNumber(1), flags = allon)
        w_Global.Prototype = w_ObjPrototype
        
        w_Object.Put(ctx, 'prototype', w_ObjPrototype, flags = allon)
        w_Global.Put(ctx, 'Object', w_Object)
        
        w_Function.Put(ctx, 'prototype', w_FncPrototype, flags = allon)
        w_Function.Put(ctx, 'constructor', w_Function, flags=allon)
        
        toString = W_ToString(ctx)
        
        put_values(ctx, w_ObjPrototype, {
            'constructor': w_Object,
            '__proto__': w_Null,
            'toString': toString,
            'toLocaleString': toString,
            'valueOf': W_ValueOf(ctx),
            'hasOwnProperty': W_HasOwnProperty(ctx),
            'isPrototypeOf': W_IsPrototypeOf(ctx),
            'propertyIsEnumerable': W_PropertyIsEnumerable(ctx),
        })
        
        #properties of the function prototype
        put_values(ctx, w_FncPrototype, {
            'constructor': w_Function,
            '__proto__': w_FncPrototype,
            'toString': W_FToString(ctx),
            'apply': W_Apply(ctx),
            'call': W_Call(ctx),
            'arguments': w_Null,
            'valueOf': W_ValueOf(ctx),
        })
        
        w_Boolean = W_BooleanObject('Boolean', w_FncPrototype)
        w_Boolean.Put(ctx, 'constructor', w_FncPrototype, flags = allon)
        w_Boolean.Put(ctx, 'length', W_IntNumber(1), flags = allon)
        
        w_BoolPrototype = create_object(ctx, 'Object', Value=newbool(False))
        w_BoolPrototype.Class = 'Boolean'
        
        put_values(ctx, w_BoolPrototype, {
            'constructor': w_FncPrototype,
            '__proto__': w_ObjPrototype,
            'toString': W_BooleanValueToString(ctx),
            'valueOf': get_value_of('Boolean')(ctx),
        })

        w_Boolean.Put(ctx, 'prototype', w_BoolPrototype, flags = allon)
        w_Global.Put(ctx, 'Boolean', w_Boolean)

        #Number
        w_Number = W_NumberObject('Number', w_FncPrototype)

        w_empty_fun = w_Function.Call(ctx, args=[W_String('')])

        w_NumPrototype = create_object(ctx, 'Object', Value=W_FloatNumber(0.0))
        w_NumPrototype.Class = 'Number'
        put_values(ctx, w_NumPrototype, {
            'constructor': w_Number,
            '__proto__': w_empty_fun,
            'toString': W_NumberValueToString(ctx),
            'valueOf': get_value_of('Number')(ctx),
        })

        put_values(ctx, w_Number, {
            'constructor': w_FncPrototype,
            'prototype': w_NumPrototype,
            '__proto__': w_FncPrototype,
            'length'   : W_IntNumber(1),
        })
        w_Number.propdict['prototype'].flags |= RO
        w_Number.Put(ctx, 'MAX_VALUE', W_FloatNumber(1.7976931348623157e308), flags = RO|DD)
        w_Number.Put(ctx, 'MIN_VALUE', W_FloatNumber(0), flags = RO|DD)
        w_Number.Put(ctx, 'NaN', W_FloatNumber(NAN), flags = RO|DD)
        # ^^^ this is exactly in test case suite
        w_Number.Put(ctx, 'POSITIVE_INFINITY', W_FloatNumber(INFINITY), flags = RO|DD)
        w_Number.Put(ctx, 'NEGATIVE_INFINITY', W_FloatNumber(-INFINITY), flags = RO|DD)
        

        w_Global.Put(ctx, 'Number', w_Number)
        
                
        #String
        w_String = W_StringObject('String', w_FncPrototype)

        w_StrPrototype = create_object(ctx, 'Object', Value=W_String(''))
        w_StrPrototype.Class = 'String'
        w_StrPrototype.Put(ctx, 'length', W_IntNumber(0))
        
        put_values(ctx, w_StrPrototype, {
            'constructor': w_String,
            '__proto__': w_StrPrototype,
            'toString': W_StringValueToString(ctx),
            'valueOf': get_value_of('String')(ctx),
            'charAt': W_CharAt(ctx),
            'charCodeAt': W_CharCodeAt(ctx),
            'concat': W_Concat(ctx),
            'indexOf': W_IndexOf(ctx),
            'lastIndexOf': W_LastIndexOf(ctx),
            'substring': W_Substring(ctx),
            'split': W_Split(ctx),
            'toLowerCase': W_ToLowerCase(ctx),
            'toUpperCase': W_ToUpperCase(ctx)
        })
        
        w_String.Put(ctx, 'prototype', w_StrPrototype, flags=allon)
        w_String.Put(ctx, 'fromCharCode', W_FromCharCode(ctx))
        w_Global.Put(ctx, 'String', w_String)

        w_Array = W_ArrayObject('Array', w_FncPrototype)

        w_ArrPrototype = W_Array(Prototype=w_ObjPrototype)
        
        put_values(ctx, w_ArrPrototype, {
            'constructor': w_FncPrototype,
            '__proto__': w_ArrPrototype,
            'toString': W_ArrayToString(ctx),
            'join': W_ArrayJoin(ctx),
            'reverse': W_ArrayReverse(ctx),
            'sort': W_ArraySort(ctx),
        })
        
        w_Array.Put(ctx, 'prototype', w_ArrPrototype, flags = allon)
        w_Array.Put(ctx, '__proto__', w_FncPrototype, flags = allon)
        w_Array.Put(ctx, 'length', W_IntNumber(1), flags = allon)
        w_Global.Put(ctx, 'Array', w_Array)
        
        
        #Math
        w_math = W_Object(Class='Math')
        w_Global.Put(ctx, 'Math', w_math)
        w_math.Put(ctx, '__proto__',  w_ObjPrototype)
        w_math.Put(ctx, 'prototype', w_ObjPrototype, flags = allon)
        w_math.Put(ctx, 'abs', W_Builtin(absjs, Class='function'))
        w_math.Put(ctx, 'floor', W_Builtin(floorjs, Class='function'))
        w_math.Put(ctx, 'pow', W_Builtin(powjs, Class='function'))
        w_math.Put(ctx, 'sqrt', W_Builtin(sqrtjs, Class='function'))
        w_math.Put(ctx, 'E', W_FloatNumber(math.e), flags=allon)
        w_math.Put(ctx, 'LN2', W_FloatNumber(math.log(2)), flags=allon)
        w_math.Put(ctx, 'LN10', W_FloatNumber(math.log(10)), flags=allon)
        log2e = math.log(math.e) / math.log(2) # rpython supports log with one argument only
        w_math.Put(ctx, 'LOG2E', W_FloatNumber(log2e), flags=allon)
        w_math.Put(ctx, 'LOG10E', W_FloatNumber(math.log10(math.e)), flags=allon)
        w_math.Put(ctx, 'PI', W_FloatNumber(math.pi), flags=allon)
        w_math.Put(ctx, 'SQRT1_2', W_FloatNumber(math.sqrt(0.5)), flags=allon)
        w_math.Put(ctx, 'SQRT2', W_FloatNumber(math.sqrt(2)), flags=allon)
        w_Global.Put(ctx, 'version', W_Builtin(versionjs), flags=allon)
        
        #Date
        w_Date = W_DateFake(ctx, Class='Date')
        w_Global.Put(ctx, 'Date', w_Date)
        
        w_Global.Put(ctx, 'NaN', W_FloatNumber(NAN), flags = DE|DD)
        w_Global.Put(ctx, 'Infinity', W_FloatNumber(INFINITY), flags = DE|DD)
        w_Global.Put(ctx, 'undefined', w_Undefined, flags = DE|DD)        
        w_Global.Put(ctx, 'eval', W_Eval(ctx))
        w_Global.Put(ctx, 'parseInt', W_ParseInt(ctx))
        w_Global.Put(ctx, 'parseFloat', W_ParseFloat(ctx))
        w_Global.Put(ctx, 'isNaN', W_Builtin(isnanjs))
        w_Global.Put(ctx, 'isFinite', W_Builtin(isfinitejs))            
        w_Global.Put(ctx, 'print', W_Builtin(printjs))
        w_Global.Put(ctx, 'unescape', W_Builtin(unescapejs))

        w_Global.Put(ctx, 'this', w_Global)

        # DEBUGGING
        if 0:
            w_Global.Put(ctx, 'pypy_repr', W_Builtin(pypy_repr))
        
        self.global_context = ctx
        self.w_Global = w_Global
        self.w_Object = w_Object

    def run(self, script, interactive=False):
        """run the interpreter"""
        bytecode = JsCode()
        script.emit(bytecode)
        if not we_are_translated():
            # debugging
            self._code = bytecode
        if interactive:
            return bytecode.run(self.global_context, retlast=True)
        else:
            bytecode.run(self.global_context)
