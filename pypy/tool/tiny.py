import re
import unittest
import parser


#  d is the dictionary of unittest changes, keyed to the old name
#  used by unittest.  d['new'] is the new replacement function, and
#  d['change type'] is one of the following functions
#           namechange_only   e.g.  assertRaises  becomes raises 
#           strip_parens      e.g.  assert_(expr) becomes assert expr
#           fail_special      e.g.  fail() becomes raise AssertionError
#           comma to op       e.g.  assertEquals(l, r) becomes assert l == r
#           rounding          e.g.  assertAlmostEqual(l, r) becomes
#                                     assert round(l - r, 7) == 0
#  Finally, 'op' is the operator you will substitute, if applicable.

# First define the functions you want to dispatch

def namechange_only(old, new, block):
    # dictionary dispatch function.
    # this is the simplest of changes.
    return re.sub('self.'+old, new, block)

def strip_parens(old, new, block):
    # dictionary dispatch function.

    pat = re.search(r'^(\s*)', block)
    indent = pat.group()
    pat = re.search('self.' + old + r'\(', block)
    rest = block[pat.end():]

    expr, trailer = get_expr(rest, ')')

    try:
        parser.expr(expr) # the parens came off easily
        return indent + new + ' ' + expr + trailer

    except SyntaxError:

        # now we have to go to work.  It would be nice if we could
        # just keep the parens, since the original author probably
        # used them to group things nicely in a complicated multi-line
        # expression.
        #
        # There is one hitch.
        #
        # self.assertx_(0, string) prints the string, as does
        # assert 0, string .  But not only does assert(0, string) not
        # print the string, it also doesn't print the AssertionError
        # either.  So nothing for it, we have to paste continuation
        # backslashes on our multiline constructs.

        try:
            realexpr, s = get_expr(expr, ',')

            # aha. we found an expr followed by a ', something_else'
            # we should probably test to make sure that something_else
            # is a string, and not, say, another expr.  But the whole
            # question of what to do when your input is bogus requires
            # more thought than I want to do at this hour ...
            # Given that assert 0, range(10) is legal, and prints
            # AssertionError: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9], is it
            # even true that s has to be a string?

            expr_w_slash = re.sub(r'\n', r'\\\n', realexpr)

            if s[0] == '\n':  # that needs a slash too ...
                return indent + new + ' ' + expr_w_slash + ',\\' + s + trailer
            else:
                return indent + new + ' ' + expr_w_slash + ',' + s + trailer

        except SyntaxError:
            # we couldn't find a 'expr, string' so it is
            # probably just a regular old multiline expression
            # t.ex. self.assertx(0
            #                    +f(x)
            #                    +g(x))

            expr_w_slash = re.sub(r'\n', r'\\\n', expr)
            return indent + new + ' ' +  expr_w_slash + trailer

def fail_special(old, new, block):
    # dictionary dispatch function.
    # while assert_() is  an error, fail() and
    # fail('message') are just fine.
    return re.sub('self.'+old, new, block)
    

def get_expr(s, char):
    # read from the beginning of the string until you get an expression.
    # return it, and the stuff left over, minus the char you separated on
    pos = pos_finder(s, char)
     
    for p in pos:
        try:
            parser.expr('(' + s[:p] + ')')
            return s[:p], s[p+1:]
        except SyntaxError: # It's not an expression yet
            pass
    raise SyntaxError       # We never found anything that worked.

def pos_finder(s, char=','):
    # returns the list of string positions where the char 'char' was found
    pos=[]
    for i in range(len(s)):
        if s[i] == char:
            pos.append(i)
    return pos

d={}

#def assertRaises(self, excClass, callableObj, *args, **kwargs)

d['assertRaises'] = {'new': 'raises',
                     'change type': namechange_only,
                     'op': None}

d['failUnlessRaises'] = d['assertRaises']

d['assert_'] = {'new': 'assert',
                'change type': strip_parens,
                'op': None}

d['failUnless'] = d['assert_']
                        

d['failIf'] = {'new': 'assert not',
               'change type': strip_parens,
               'op': None}

d['fail'] = {'old': 'fail',
             'new': 'raise AssertionError ',
             'change type': fail_special,
             'op': None}

"""

d['failUnlessEqual'] = {'old': 'failUnlessEqual',
                        'new': 'assert not',
                        'change type': 'comma to op',
                        'op': '!='}

d['failIfEqual'] = {'old': 'failIfEqual',
                    'new': 'assert not',
                    'change type': 'comma to op',
                    'op': '=='}

d['assertEquals'] = {'old': 'assertEquals',
                     'new': 'assert',
                     'change type': 'comma to op',
                     'op': '=='}

d['assertNotEqual'] = {'old': 'assertNotEqual',
                       'new': 'assert',
                       'change type': 'comma to op',
                       'op': '!='}

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

d['assertNotEquals'] = {'old': 'assertNotEquals',
                        'new': 'assert',
                        'change type':
                        'comma to op',
                        'op': '!='}

d['assertEqual'] = {'old': 'assertEqual',
                    'new': 'assert',
                    'change type': 'comma to op',
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
        return d[key]['change type'](key, d[key]['new'], s)
    else:
        return s

def which_comma(tuplelist):
    import parser

    # make the python parser do the hard work of deciding which comma
    # splits the string into two expressions

    for l, r in tuplelist:
        try:

            parser.expr(l + ')')
            parser.expr('(' + r)
            return l , r    # Great!  Both sides are expressions!
        except SyntaxError: # It wasn't that comma
            pass
    raise SyntaxError       # We never found anything that worked.

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
        self.assertEquals(process_block("self.assert_(x)"),
                          "assert x")
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
                                 Snake!  It's a snake!
                              ''') # multiline, must remove the parens
            """
            ),
            r"""
            assert not 0 + 0\
                         + len('badger\n')\
                         + 0, '''badger badger badger badger
                                 mushroom mushroom
                                 Snake!  It's a snake!
                              ''' # multiline, must remove the parens
            """
            )

if __name__ == '__main__':
    unittest.main()
    #for block in  blocksplitter('xxx.py'): print process_block(block)


