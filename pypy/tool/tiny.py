import re
import unittest


#  d is the dictionary of unittest changes, keyed to the old name
#  used by unittest.  d['new'] is the new replacement function, and
#  d['change type'] is one of the following functions
#           namechange_only   e.g.  assertRaises  becomes raises 
#           strip_parens      e.g.  assert_(expr) becomes assert expr
#           comma to op       e.g.  assertEquals(l, r) becomes assert l == r
#           rounding          e.g.  assertAlmostEqual(l, r) becomes
#                                     assert round(l - r, 7) == 0
#  Finally, 'op' is the operator you will substitute, if applicable.

# First define the functions you want to dispatch

def namechange_only(old, new, block):
    # this is the simplest of changes.
    return re.sub('self.'+old, new, block)

def strip_parens(old, new, block):
    return re.sub('self.'+old, new, block)

d={}

#def assertRaises(self, excClass, callableObj, *args, **kwargs)

d['assertRaises'] = {'new': 'raises',
                     'change type': namechange_only,
                     'op': None}

d['failUnlessRaises'] = d['assertRaises']

d['assert_'] = {'new': 'assert',
                'change type': strip_parens,
                'op': None}

"""
d['failUnless'] = {'old':'failUnless',
                   'new': 'assert',
                   'change type': 'strip_parens',
                   'op': None}

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

d['failIf'] = {'old': 'failIf',
               'new': 'assert not',
               'change type': 'strip_parens',
               'op': None}

d['fail'] = {'old': 'fail',
             'new': 'raise AssertionError ',
             'change type': 'strip_parens',
             'op': None}

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
    #print 'found the block ', block
    f = old_names.match(s)
    if f:
        key = f.group(0).lstrip()[5:-1]  # '\tself.blah(' -> 'blah'
        return d[key]['change type'](key, d[key]['new'], s)
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
            self.assertRaises(TypeError, func, 42, {'arg1': 23})
            """
            ),
            """
            raises(TypeError, func, 42, {'arg1': 23})
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
            
        

if __name__ == '__main__':
    unittest.main()
    #for block in  blocksplitter('xxx.py'): print process_block(block)


