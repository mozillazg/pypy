import re
import unittest
import parser


#  d is the dictionary of unittest changes, keyed to the old name
#  used by unittest.  d['new'] is the new replacement function, and
#  d['change type'] is one of the following functions
#           namechange_only   e.g.  assertRaises  becomes raises
#           fail_special      e.g.  fail() becomes raise AssertionError
#           strip_parens      e.g.  assert_(expr) becomes assert expr
#           comma_to_op       e.g.  assertEquals(l, r) becomes assert l == r
#           rounding          e.g.  assertAlmostEqual(l, r) becomes
#                                     assert round(l - r, 7) == 0
#  Finally, 'op' is the operator you will substitute, if applicable.

# First define the functions you want to dispatch

def namechange_only(old, new, block, op):
    # dictionary dispatch function.
    # this is the simplest of changes.
    return re.sub('self.'+old, new, block)

def fail_special(old, new, block, op):
    # dictionary dispatch function.
    pat = re.search(r'^(\s*)', block)
    indent = pat.group()
    pat = re.search('self.' + old + r'\(', block)
    rest = block[pat.end():]

    expr, trailer = get_expr(rest, ')')

    if expr == '':  # fail()  --> raise AssertionError
         return indent + new + trailer
    else:   # fail('Problem')  --> raise AssertionError, 'Problem'
         return indent + new + ', ' + expr + trailer

def strip_parens(old, new, block, op):
    # dictionary dispatch function.
    return_dict={}
    pat = re.search(r'^(\s*)', block)
    indent = pat.group()
    pat = re.search('self.' + old + r'\(', block)
    rest = block[pat.end():]

    expr, trailer = get_expr(rest, ')')
    extra = ''

    try:
        parser.expr(expr) # the parens came off easily

    except SyntaxError:
        # self.assertx_(0, string) prints the string, as does
        # assert 0, string .  But assert(0, string) prints
        # neither the string, nor the AssertionError !  So we have
        # to paste continuation backslashes on our multiline constructs.

        try:
            left, right = get_expr(expr, ',')

            # aha. we found an expr followed by a ', something_else'
            # we should probably test to make sure that something_else
            # is a string, and not, say, another expr.  But the whole
            # question of what to do when your input is bogus requires
            # more thought than I want to do at this hour ...
            # Given that assert 0, range(10) is legal, and prints
            # AssertionError: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9], is it
            # even true that right has to be a string?

            expr = re.sub(r'\n', r'\\\n', left)
            
            if right[0] == '\n':  # that needs a slash too ...
                extra = ',\\' + right
            else:
                extra = ',' + right

        except SyntaxError:
            # we couldn't find a 'expr, string' so it is
            # probably just a regular old multiline expression
            # e.g   self.assertx(0
            #                    +f(x)
            #                    +g(x))

            expr = re.sub(r'\n', r'\\\n', expr)

    return indent + new + ' ' + expr + extra + trailer

def comma_to_op(old, new, block, op):
    # dictionary dispatch function.  get_expr does all the work.

    pat = re.search(r'^(\s*)', block)
    indent = pat.group()
    pat = re.search('self.' + old + r'\(', block)
    rest = block[pat.end():]

    expr, trailer = get_expr(rest, ')')
    left, right = get_expr(expr, ',')
    #print 'left is <%s>, right is <%s>' % (left, right)

    try:
        parser.expr(left)  # that paren came off easily
        left = left + ' ' + op
    except SyntaxError:
        left  = re.sub(r'\n', r'\\\n', left + ' ' + op)
        #if right[0] == '\n':  # that needs a slash too ...
        #    left  += '\\'
    try:
        parser.expr(right)  # that paren came off easily
    except SyntaxError:
        right = re.sub(r'\n', r'\\\n', right)

    return indent + new + ' ' + left + right + trailer

def get_expr(s, char):
    # used by fail_special, real_strip_parens, comma_to_op
    # read from the beginning of the string until you get an expression.
    # return it, and the stuff left over, minus the char you separated on
    pos = pos_finder(s, char)

    if pos == []:
        raise SyntaxError # we didn't find the expected char.  Ick.
     
    for p in pos:
        # make the python parser do the hard work of deciding which comma
        # splits the string into two expressions
        try:
            parser.expr('(' + s[:p] + ')')
            return s[:p], s[p+1:]
        except SyntaxError: # It's not an expression yet
            pass
    raise SyntaxError       # We never found anything that worked.

def pos_finder(s, char=','):
    # used by find_expr
    # returns the list of string positions where the char 'char' was found
    pos=[]
    for i in range(len(s)):
        if s[i] == char:
            pos.append(i)
    return pos

d={}

d['assertRaises'] = {'new': 'raises',
                     'change type': namechange_only,
                     'op': None}

d['failUnlessRaises'] = d['assertRaises']

d['fail'] = {'new': 'raise AssertionError',
             'change type': fail_special,
             'op': None}

d['assert_'] = {'new': 'assert',
                'change type': strip_parens,
                'op': None}

d['failUnless'] = d['assert_']

d['failIf'] = {'new': 'assert not',
               'change type': strip_parens,
               'op': None}

d['assertEqual'] = {'new': 'assert',
                     'change type': comma_to_op,
                     'op': '=='}

d['assertEquals'] = d['assertEqual']


d['assertNotEqual'] = {'new': 'assert',
                        'change type':comma_to_op,
                        'op': '!='}

d['assertNotEquals'] = d['assertNotEqual']

d['failUnlessEqual'] = {'new': 'assert not',
                        'change type': comma_to_op,
                        'op': '!='}
d['failIfEqual'] = {'new': 'assert not',
                    'change type': comma_to_op,
                    'op': '=='}

"""

d['assertNotAlmostEqual'] = {'old': 'assertNotAlmostEqual',
                             'new': 'assert round',
                             'change type': 'rounding',
                             'op': '!='}

d['assertNotAlmostEquals'] = {'old': 'assertNotAlmostEquals',
                              'new': 'assert round',
                              'change type': 'rounding',
                              'op': '!='}

d['failUnlessAlmostEqual'] = {'old': 'failUnlessAlmostEqual',
                              'new': 'assert not round',
                              'change type': 'rounding',
                              'op': '=='}

d['assertUnlessAlmostEquals'] = {'old': 'assertUnlessAlmostEquals',
                                 'new': 'assert round',
                                 'change type': 'rounding',
                                 'op': '=='}

d['assertAlmostEqual'] = {'old': 'assertAlmostEqual',
                          'new': 'assert round',
                          'change type': 'rounding',
                          'op': '=='}
"""
leading_spaces = re.compile(r'^(\s*)')

pat = ''
for k in d.keys():
    pat += '|' + r'^(\s*)' + 'self.' + k + r'\(' # \tself.whatever(

old_names = re.compile(pat[1:])  # strip the extra '|' from front

def blocksplitter(filename):

    fp = file(filename, 'r')
    blocklist = []
    blockstring = ''

    for line in fp:

        interesting = old_names.match(line)

        if interesting :
            if blockstring:
                blocklist.append(blockstring)
                blockstring = line # reset the block
        else:
            blockstring += line
            
    blocklist.append(blockstring)
    return blocklist

def process_block(s):
    f = old_names.match(s)
    if f:
        key = f.group(0).lstrip()[5:-1]  # '\tself.blah(' -> 'blah'
        # now do the dictionary dispatch.
        return d[key]['change type'](key, d[key]['new'], s, d[key] ['op'])
    else:
        return s

class Testit(unittest.TestCase):
    def test(self):
        self.assertEquals(process_block("badger badger badger"),
                          "badger badger badger")

        self.assertEquals(process_block(
            "self.assertRaises(excClass, callableObj, *args, **kwargs)"
            ),
            "raises(excClass, callableObj, *args, **kwargs)"
                          )

        self.assertEquals(process_block(
            """
            self.failUnlessRaises(TypeError, func, 42, **{'arg1': 23})
            """
            ),
            """
            raises(TypeError, func, 42, **{'arg1': 23})
            """
                          )
        self.assertEquals(process_block(
            """
            self.assertRaises(TypeError,
                              func,
                              mushroom)
            """
            ),
            """
            raises(TypeError,
                              func,
                              mushroom)
            """
                          )
        self.assertEquals(process_block("self.fail()"), "raise AssertionError")
        self.assertEquals(process_block("self.fail('mushroom, mushroom')"),
                          "raise AssertionError, 'mushroom, mushroom'")
        self.assertEquals(process_block("self.assert_(x)"), "assert x")
        self.assertEquals(process_block("self.failUnless(func(x)) # XXX"),
                          "assert func(x) # XXX")
        
        self.assertEquals(process_block(
            """
            self.assert_(1 + f(y)
                         + z) # multiline, add continuation backslash
            """
            ),
            r"""
            assert 1 + f(y)\
                         + z # multiline, add continuation backslash
            """
                          )

        self.assertEquals(process_block("self.assert_(0, 'badger badger')"),
                          "assert 0, 'badger badger'")

        self.assertEquals(process_block(
            r"""
            self.assert_(0,
                 'Meet the badger.\n')
            """
            ),
            r"""
            assert 0,\
                 'Meet the badger.\n'
            """
                          )
        
        self.assertEquals(process_block(
            r"""
            self.failIf(0 + 0
                          + len('badger\n')
                          + 0, '''badger badger badger badger
                                 mushroom mushroom
                                 Snake!  Ooh a snake!
                              ''') # multiline, must remove the parens
            """
            ),
            r"""
            assert not 0 + 0\
                          + len('badger\n')\
                          + 0, '''badger badger badger badger
                                 mushroom mushroom
                                 Snake!  Ooh a snake!
                              ''' # multiline, must remove the parens
            """
                          )

        self.assertEquals(process_block("self.assertEquals(0, 0)"),
                          "assert 0 == 0")
        
        self.assertEquals(process_block(
            r"""
            self.assertEquals(0,
                 'Run away from the snake.\n')
            """
            ),
            r"""
            assert 0 ==\
                 'Run away from the snake.\n'
            """
                          )

        self.assertEquals(process_block(
            r"""
            self.assertEquals(badger + 0
                              + mushroom
                              + snake, 0)
            """
            ),
            r"""
            assert badger + 0\
                              + mushroom\
                              + snake == 0
            """
                          )
                            
        self.assertEquals(process_block(
            r"""
            self.assertNotEquals(badger + 0
                              + mushroom
                              + snake,
                              mushroom
                              - badger)
            """
            ),
            r"""
            assert badger + 0\
                              + mushroom\
                              + snake !=\
                              mushroom\
                              - badger
            """
                          )

        self.assertEqual(process_block(
            r"""
            self.assertEquals(badger(),
                              mushroom()
                              + snake(mushroom)
                              - badger())
            """
            ),
            r"""
            assert badger() ==\
                              mushroom()\
                              + snake(mushroom)\
                              - badger()
            """
                         )
        self.assertEquals(process_block("self.failIfEqual(0, 0)"),
                          "assert not 0 == 0")

        self.assertEquals(process_block("self.failUnlessEqual(0, 0)"),
                          "assert not 0 != 0")
                              
if __name__ == '__main__':
    unittest.main()
    #for block in  blocksplitter('xxx.py'): print process_block(block)
