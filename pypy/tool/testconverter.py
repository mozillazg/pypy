import re
import unittest

old= 'self.assertEquals'
new= 'assert'
old_function = re.compile(r'^(\s*)' + old + r'\((.*)')
leading_spaces = re.compile(r'^(\s*)')


def convert(s, old, new):

    compile(s.lstrip(), '', 'exec')
    body = s.replace(old, '', 1).lstrip()
    plist = pos_finder(body, ',')

    if plist == []:
        raise SyntaxError , "Could not find a ',' in %s" % body
    else:
        arglist = []
        for p in plist:
            l, r = body[:p], body[p+1:]
            arglist.append((l, r))

        l, r = which_comma(arglist)

        if r.rstrip()[-1] != ')':
            # if the last printing char of the string is not ')',
            # keep the parens for now.  This could be refined.
            return new + l + ') == (' + r

        else:  # see if we can drop one set of parens

            stripped = r.rstrip()
            line_ends = r[len(stripped):]
            block = new + ' ' + l[1:] + ' == ' + stripped[0:-1] + line_ends
            try:
                compile(block, '', 'exec')
                return block
            except SyntaxError: # too bad, needed them
                return new + l + ') == (' + r
        
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
                try:
                    backstring = convert(blockstring, old, new)
                    filestring += indent + backstring
                except SyntaxError:
                    filestring += blockstring # malformed, copy as written
                
            blockstring = line # reset the block
            indent = ls.group(1)
            was_interesting = True

        elif not was_interesting and not interesting :
            # the last line was not interesting and this one isn't either.

            filestring  += line

        else:
            # the slightly-hard case:
            # is this line a continuation of the current interesting block?
            # or is it just another uninteresting line that follows it?

            try:
                filestring += indent + convert(blockstring, old, new)
                # We were done.  This is a boring old follower

                filestring += line
                was_interesting = False

            except SyntaxError:  # we haven't got enough yet.
                blockstring += line

    if was_interesting :
        try:
            filestring += indent + convert(blockstring, old, new)
        except SyntaxError:
            print 'last block %s was malformed' % blockstring.rstrip()
            filestring += blockstring
    
    print filestring

if __name__ == '__main__':
    #unittest.main()
    blocksplitter('xxx.py')
