"""Snippets for translation

This module holds various snippets, to be used by translator
unittests.

TODO, or sanxiyn's plan:

Each snippet should know about suitable arguments to test it.
(Otherwise, there's a duplcation!) Should the result also be
stored? It can computed by CPython if we don't store it.

In case of typed translation test, we can give input_arg_types
by actually trying type() on arguments.

Each unittest should define a list of functions which it is able
to translate correctly, and import the list for tests. When
a translator can handle more, simply adding a function to the
list should suffice.

But for now, none of the above applies.
"""
function_info={
 'append_five':{'arg_names': ['lst'],'arg_types':[list],
               'name': 'append_five'},
 'branch_id': {'arg_names': ['cond', 'a', 'b'],'arg_types':[int,int,int],
               'name': 'branch_id'},
 'break_continue': {'arg_names': ['x'],'arg_types':[int],
                    'name': 'break_continue'},
 'build_instance': {'arg_names': [],'arg_types':[],
                    'name': 'build_instance'},
 'builtinusage': {'arg_names': [],'arg_types':[],
                  'name': 'builtinusage'},
 'call_five': {'arg_names': [],'arg_types':[],
                    'name': 'call_five'},
 'choose_last': {'arg_names': [],'arg_types':[],
                 'name': 'choose_last'},
 'factorial': {'arg_names': ['n'],'arg_types':[int],
               'name': 'factorial'},
 'factorial2': {'arg_names': ['n'],'arg_types':[int],
                'name': 'factorial2'},
 'finallys': {'arg_names': ['lst'],'arg_types':[list],
              'name': 'finallys'},
 'greet': {'arg_names': ['target'],'arg_types':[str],
           'name': 'greet'},
 'half_of_n': {'arg_names': ['n'],'arg_types':[int],
               'name': 'half_of_n'},
 'if_then_else': {'arg_names': ['cond', 'x', 'y'],
                     'arg_types':[object,object,object],
                  'name': 'if_then_else'},
 'inheritance1': {'arg_names': [],'arg_types':[],
                  'name': 'inheritance1'},
 'inheritance2': {'arg_names': [],'arg_types':[],
                  'name': 'inheritance2'},
 #'inheritance_nonrunnable': {'arg_names': [],'arg_types':[],
 #                            'name': 'inheritance_nonrunnable'},
 'int_id': {'arg_names': ['x'],'arg_types':[int],
            'name': 'int_id'},
 'is_perfect_number': {'arg_names': ['i'],'arg_types':[int],
                    'name': 'is_perfect_number'},
 'knownkeysdict': {'arg_names': ['b'],'arg_types':[object],
                   'name': 'knownkeysdict'},
 'merge_setattr': {'arg_names': ['x'],'arg_types':[object],
                   'name': 'merge_setattr'},
# 'methodcall1': {'arg_names': ['cond'],'arg_types':[int],
#                   'name': 'methodcall1'},
 'my_bool': {'arg_names': ['x'],'arg_types':[object],
             'name': 'my_bool'},
 'my_gcd': {'arg_names': ['a', 'b'],'arg_types':[int,int],
            'name': 'my_gcd'},
 'nested_whiles': {'arg_names': ['i', 'j'],'arg_types':[int,int],
                   'name': 'nested_whiles'},
 'poly_branch': {'arg_names': ['x'],'arg_types':[object],
                 'name': 'poly_branch'},
 'poor_man_range': {'arg_names': ['i'],'arg_types':[int],
                    'name': 'poor_man_range'},
 'poor_man_rev_range': {'arg_names': ['i'],'arg_types':[int],
                    'name': 'poor_man__rev_range'},
 'powerset': {'arg_names': ['x'],'arg_types':[int],
                 'name': 'powerset'},
 'prime': {'arg_names': ['n'],'arg_types':[int],
           'name': 'prime'},
 'reverse_3': {'arg_names': ['lst'],'arg_types':[list],
               'name': 'reverse_3'},
 's_and': {'arg_names': ['x', 'y'],'arg_types':[object,object],
           'name': 's_and'},
 'set_attr': {'arg_names': [],'arg_types':[],
              'name': 'set_attr'},
 'sieve_of_eratosthenes': {'arg_names': [],'arg_types':[],
                           'name': 'sieve_of_eratosthenes'},
 'simple_func': {'arg_names': ['i'],'arg_types':[int],
                 'name': 'simple_func'},
 'simple_id': {'arg_names': ['x'],'arg_types':[object],
               'name': 'simple_id'},
 'simple_method': {'arg_names': ['v'],'arg_types':[object],
                   'name': 'simple_method'},
# 'somebug1': {'arg_names': ['n'],'arg_types':[int],
#              'name': 'somebug1'},
 'time_waster': {'arg_names': ['n'],'arg_types':[int],
                 'name': 'time_waster'},
 'two_plus_two': {'arg_names': [],'arg_types':[],
                  'name': 'two_plus_two'},
 'while_func': {'arg_names': ['i'],'arg_types':[int],
                'name': 'while_func'},
 'yast': {'arg_names': ['lst'],'arg_types':[list],
          'name': 'yast'}
 }

def if_then_else(cond, x, y):
    if cond:
        return x
    else:
        return y

def my_gcd(a, b):
    r = a % b
    while r:
        a = b
        b = r
        r = a % b
    return b

def is_perfect_number(n):
    div = 1
    sum = 0
    while div < n:
        if n % div == 0:
            sum += div
        div += 1
    return n == sum

def my_bool(x):
    return not not x

def two_plus_two():
    """Array test"""
    array = [0] * 3
    array[0] = 2
    array[1] = 2
    array[2] = array[0] + array[1]
    return array[2]

def sieve_of_eratosthenes():
    """Sieve of Eratosthenes
    
    This one is from an infamous benchmark, "The Great Computer
    Language Shootout".

    URL is: http://www.bagley.org/~doug/shootout/
    """
    flags = [True] * (8192+1)
    count = 0
    i = 2
    while i <= 8192:
        if flags[i]:
            k = i + i
            while k <= 8192:
                flags[k] = False
                k = k + i
            count = count + 1
        i = i + 1
    return count

def simple_func(i):
    return i + 1

def while_func(i):
    total = 0
    while i > 0:
        total = total + i
        i = i - 1
    return total

def nested_whiles(i, j):
    s = ''
    z = 5
    while z > 0:
        z = z - 1
        u = i
        while u < j:
            u = u + 1
            s = s + '.'
        s = s + '!'
    return s

def poor_man_range(i):
    lst = []
    while i > 0:
        i = i - 1
        lst.append(i)
    lst.reverse()
    return lst

def poor_man_rev_range(i):
    lst = []
    while i > 0:
        i = i - 1
        lst += [i]
    return lst

def simple_id(x):
    return x

def branch_id(cond, a, b):
    while 1:
        if cond:
            return a
        else:
            return b

def builtinusage():
    return pow(2, 2)

def yast(lst):
    total = 0
    for z in lst:
        total = total + z
    return total

def time_waster(n):
    """Arbitrary test function"""
    i = 0
    x = 1
    while i < n:
        j = 0
        while j <= i:
            j = j + 1
            x = x + (i & j)
        i = i + 1
    return x

def half_of_n(n):
    """Slice test"""
    i = 0
    lst = range(n)
    while lst:
        lst = lst[1:-1]
        i = i + 1
    return i

def int_id(x):
    i = 0
    while i < x:
        i = i + 1
    return i

def greet(target):
    """String test"""
    hello = "hello"
    return hello + target

def choose_last():
    """For loop test"""
    set = ["foo", "bar", "spam", "egg", "python"]
    for choice in set:
        pass
    return choice

def poly_branch(x):
    if x:
        y = [1,2,3]
    else:
        y = ['a','b','c']

    z = y
    return z*2

def s_and(x, y):
    if x and y:
        return 'yes'
    else:
        return 'no'

def break_continue(x):
    result = []
    i = 0
    while 1:
        i = i + 1
        try:
            if i&1:
                continue
            if i >= x:
                break
        finally:
            result.append(i)
        i = i + 1
    return result

def reverse_3(lst):
    try:
        a, b, c = lst
    except:
        return 0, 0, 0
    return c, b, a

def finallys(lst):
    x = 1
    try:
        x = 2
        try:
            x = 3
            a, = lst
            x = 4
        except KeyError:
            return 5
        except ValueError:
            return 6
        b, = lst
        x = 7
    finally:
        x = 8
    return x

def factorial(n):
    if n <= 1:
        return 1
    else:
        return n * factorial(n-1)

def factorial2(n):   # analysed in a different order
    if n > 1:
        return n * factorial(n-1)
    else:
        return 1

def append_five(lst):
    lst += [5]
    

def call_five():
    a = []
    append_five(a)
    return a


class C(object): pass

def build_instance():
    c = C()
    return c

def set_attr():
    c = C()
    c.a = 1
    c.a = 2
    return c.a

def merge_setattr(x):
    if x:
        c = C()
        c.a = 1
    else:
        c = C()
    return c.a

class D(C): pass
class E(C): pass

def inheritance1():
    d = D()
    d.stuff = ()
    e = E()
    e.stuff = -12
    e.stuff = 3
    lst = [d, e]
    return d.stuff, e.stuff


def inheritance2():
    d = D()
    d.stuff = (-12, -12)
    e = E()
    e.stuff = (3, "world")
    return getstuff(d), getstuff(e)

class F:
    pass
class G(F):
    def m(self, x):
        return self.m2(x)
    def m2(self, x):
        return D(), x
class H(F):
    def m(self, y):
        self.attr = 1
        return E(), y

def knownkeysdict(b):
    if b:
        d = {'a': 0}
        d['b'] = b
        d['c'] = 'world'
    else:
        d = {'b': -123}
    return d['b']

def prime(n):
    return len([i for i in range(1,n+1) if n%i==0]) == 2


class Z:
    def my_method(self):
        return self.my_attribute

def simple_method(v):
    z = Z()
    z.my_attribute = v
    return z.my_method()


def powerset(setsize):
    """Powerset

    This one is from a Philippine Pythonista Hangout, an modified
    version of Andy Sy's code.
    
    list.append is modified to list concatenation, and powerset
    is pre-allocated and stored, instead of printed.
    
    URL is: http://lists.free.net.ph/pipermail/python/2002-November/
    """
    set = range(setsize)
    maxcardinality = pow(2, setsize)
    bitmask = 0L
    powerset = [None] * maxcardinality
    ptr = 0
    while bitmask < maxcardinality:
        bitpos = 1L
        index = 0
        subset = []
        while bitpos < maxcardinality:
            if bitpos & bitmask:
                subset = subset + [set[index]]
            index += 1
            bitpos <<= 1
        powerset[ptr] = subset
        ptr += 1
        bitmask += 1
    return powerset

# --------------------(Currently) Non runnable Functions ---------------------

def somebug1(n):
    l = []
    v = l.append
    while n:
        l[7] = 5
    return v

def inheritance_nonrunnable():
    d = D()
    d.stuff = (-12, -12)
    e = E()
    e.stuff = (3, "world")
    return C().stuff

# --------------------(Currently) Non compillable Functions ---------------------

def attrs():
    def b(): pass
    b.f = 4
    b.g = 5
    return b.f + b.g

def getstuff(x):
    return x.stuff

def methodcall1(cond):
    if cond:
        x = G()
    else:
        x = H()
    return x.m(42)

