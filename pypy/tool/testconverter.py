import re
import unittest

old_fname = 'self.assertEquals'
new_fname = 'assert'
old_function = re.compile(r'^(\s*)' + old_fname + r'\((.*)')
leading_spaces = re.compile(r'^(\s*)')


def process_block(s, old, new):
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

        try:
            r = find_comma(arglist)
            left, right = find_comma(arglist)

            if right.rstrip()[-1] != ')':
                # if the last printing char of the string is not ')',
                # keep the parens for now.
                return new + left + ') == (' + right
            else:  # see if we can drop one set of parens
                #stripped = right.rstrip()[0:-1]
                l = new + ' ' + left[1:] + ' == ' + right.rstrip()[0:-1] + '\n'
                try:
                    compile(l, '', 'exec')
                    return l
                except SyntaxError: # too bad, needed them
                    return new + left + ') == (' + right

        except SyntaxError:
            print 'malformed block %s cannot be converted' % s.rstrip()
            return s
        
def find_comma(tuplelist):
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
    was_interesting = False
    indent = ''
    
    for line in fp:

        ls = leading_spaces.search(line) # this will never fail
        l_spaces = ls.group(1)

        interesting = old_function.search(line)

        if interesting :
            # we have found the beginning of a new interesting block.
            # finish up your business with your last block, if 
            # necessary and reset everything

            if was_interesting:
                filestring += indent + process_block(blockstring,
                                                     old_fname, new_fname)
            blockstring = line # reset the block
            indent = ls.group(1)
            was_interesting = True

        elif not was_interesting and not interesting :
            # the last line was not interesting and this one isn't either.
            # just copy it out.
            filestring  += line

        else:
            # the slightly-hard case:
            # is this line a continuation of the current interesting block?
            # or is it just another uninteresting line that follows it?

            try:
                compile(blockstring.lstrip(), '', 'exec')
                # We were done.  This is a boring old follower
                
                filestring += indent + process_block(blockstring, old_fname, new_fname)
                filestring += line
                #blockstring = ''
                was_interesting = False

            except SyntaxError:  # we haven't got enough yet.
                blockstring += line

    if was_interesting :
        filestring += indent + process_block(blockstring, old_fname, new_fname)
    
    print filestring

if __name__ == '__main__':
    #unittest.main()
    blocksplitter('xxx.py')
