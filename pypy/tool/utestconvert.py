import re
import unittest
import parser
import os

d={}
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
#  Got to define the dispatch functions first ....

def namechange_only(old, new, block, op):
    '''rename a function.  dictionary dispatched.'''
    return re.sub('self.'+old, new, block)

d['assertRaises'] = {'new': 'raises',
                     'change type': namechange_only,
                     'op': None}

d['failUnlessRaises'] = d['assertRaises']

def fail_special(old, new, block, op):
    '''change fail function to raise AssertionError. dictionary dispatched. '''
    indent, expr, trailer = common_setup(old, block)
    
    if expr == '':  # fail()  --> raise AssertionError
         return indent + new + trailer
    else:   # fail('Problem')  --> raise AssertionError, 'Problem'
         return indent + new + ', ' + expr + trailer
     
d['fail'] = {'new': 'raise AssertionError',
             'change type': fail_special,
             'op': None}

def comma_to_op(old, new, block, op):
    '''change comma to appropriate op. dictionary dispatched. '''
    indent, expr, trailer = common_setup(old, block)
    new = new + ' '
    op = ' ' + op
    left, right = get_expr(expr, ',')

    try:
        parser.expr(left)  # that paren came off easily
    except SyntaxError:
        left  = re.sub(linesep, '\\'+linesep, left)
        
    try:
        parser.expr(right.lstrip())  # that paren came off easily
    except SyntaxError:
        right = re.sub(linesep, '\\'+linesep, right)

    if right.startswith(linesep):
        op = op + '\\'
    return indent + new + left + op + right + trailer

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

def strip_parens(old, new, block, op):
    '''remove one set of parens. dictionary dispatched. '''
    indent, expr, trailer = common_setup(old, block)
    new = new + ' '

    try:
        parser.expr(expr) # the parens came off easily
        return indent + new + expr + trailer
    except SyntaxError:
        # paste continuation backslashes on our multiline constructs.
        try:
            # is the input expr, string?
            left, right = get_expr(expr, ',')
            left = re.sub(linesep, '\\'+linesep, left)
            # since the right is a string, assume it can take care
            # of itself even if multiline.
            
            if right.startswith(linesep):# that needs a slash too ...
                between = ',\\'
            else:
                between = ','
            return indent + new + left + between + right + trailer

        except SyntaxError: # just a regular old multiline expression
            expr = re.sub(linesep, '\\'+linesep, expr)
            return indent + new + expr + trailer
        
d['assert_'] = {'new': 'assert',
                'change type': strip_parens,
                'op': None}

d['failUnless'] = d['assert_']

d['failIf'] = {'new': 'assert not',
               'change type': strip_parens,
               'op': None}
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
for k in d.keys():  # this complicated pattern to match all unittests
    pat += '|' + r'^(\s*)' + 'self.' + k + r'\(' # \tself.whatever(

old_names = re.compile(pat[1:])  # strip the extra '|' from front
linesep=os.linesep

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

def common_setup(old, block):
    '''split the block into component parts'''

    indent = re.search(r'^(\s*)', block).group()
    pat = re.search('self.' + old + r'\(', block)
    expr, trailer = get_expr(block[pat.end():], ')')
    return indent, expr, trailer

def get_expr(s, char):
    # the trick.  how to get an expression without really trying :-)
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

        self.assertEquals(process_block(
            r"""
            self.failUnlessEqual(mushroom()
                                 + mushroom()
                                 + mushroom(), '''badger badger badger badger
                                 badger badger badger badger
                                 badger badger badger badger
                                 ''') # multiline, must remove the parens
            """
            ),
            r"""
            assert not mushroom()\
                                 + mushroom()\
                                 + mushroom() != '''badger badger badger badger
                                 badger badger badger badger
                                 badger badger badger badger
                                 ''' # multiline, must remove the parens
            """
                          )
                              
if __name__ == '__main__':
    unittest.main()
    #for block in  blocksplitter('xxx.py'): print process_block(block)

