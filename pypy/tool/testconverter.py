import re
import unittest

old_fname = 'self.assertEquals'
new_fname = 'assert'
old_function = re.compile(r'^(\s*)' + old_fname + r'\((.*)')
leading_spaces = re.compile(r'^(\s*)')


def process_block(s, interesting, indentation, old, new):
    if not interesting:
        return s
    else:
        body = s.replace(old, '', 1).lstrip()
        
        if body.rstrip() == '(,)': # catch this special case early.
            print 'malformed block %s cannot be converted' % s.rstrip()
            return s
        
        plist = pos_finder(body, ',')
        if plist == []:
            print "Could not find a ',' in %s" % body
            return s
        else:
            arglist = []
            for p in plist:
                left, right = body[:p], body[p+1:]
                arglist.append((left, right))
            r = find_comma(arglist)

            if r is None:
                print 'malformed block %s cannot be converted' % s
                return s
            else:
                return indentation + new + r[0] + ') == (' + r[1]
        

def find_comma(tuplelist):
    import parser

    # make the python parser do the hard work of deciding which comma
    # splits the string into two expressions
    
    for l, r in tuplelist:
        try:
            left = l + ')'
            right = '(' + r
            parser.expr(left)
            parser.expr(right)
            return l , r  # Great!  Both sides are expressions!
        except SyntaxError: # It wasn't that comma
            pass
    return None
    
def pos_finder(s, char=','):
    # returns the list of string positions where the char 'char' was found
    pos=[]
    for i in range(len(s)):
        if s[i] == char:
            pos.append(i)
    return pos
            
def blocksplitter(filename):

    fp = file(filename, 'r')
    blockstring = ''
    filestring = ''
    current_indent = 0
    was_interesting = False
    n_l_s = ''
    
    for line in fp:

        ls = leading_spaces.search(line) # this will never fail
        l_spaces = ls.group(1)
        new_indent = len(l_spaces)

        interesting = old_function.search(line)

        if interesting :
            # we have found the beginning of a new interesting block.
            # finish up your business with your last block, and
            # reset everything

            filestring += process_block(blockstring, was_interesting,
                                        n_l_s, old_fname, new_fname)

            blockstring = line # reset the block
            current_indent = new_indent
            n_l_s = ls.group(1)
            was_interesting = True

        elif not was_interesting and not interesting :
            # the last line was not interesting and this one isn't either
            # just add it to the block

            blockstring += line

        else:
            # the slightly-hard case:
            # is this line a continuation of the current interesting block?
            # or is it just another uninteresting line that follows it?

            if new_indent > current_indent:  # continuation
                blockstring += line

                # XXXX FIXME: check for comments?  line continuations with \?
                # Will we ever need it?

            else: # boring follower
                filestring += process_block(blockstring, was_interesting,
                                            n_l_s, old_fname, new_fname)
                blockstring = line
                was_interesting = False
                
    filestring += process_block(blockstring, was_interesting, n_l_s,
                                old_fname, new_fname)
    
    print filestring

if __name__ == '__main__':
    #unittest.main()
    blocksplitter('xxx.py')
