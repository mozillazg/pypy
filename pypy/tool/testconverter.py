import re
import unittest

old_fname = 'self.assertEquals'
new_fname = 'assert'
old_function = re.compile(r'^(\s*)' + old_fname + r'\((.*)')
leading_spaces = re.compile(r'^(\s*)')

def strip_trailing(line, char=')'):
    last = line[len(line)-1]
    lastchar = last[-1]

    if lastchar != char :
        print "Stripping trailing '%s' from buf '%s', got '%s' instead!" % (
            char, line, lastchar)
        return line
    else:
        """
        buf = s.splitlines()
        for l in buf:
            if not l.startswith(indentation):
                print 'Expected %s but got %s instead' % (indentation, l)
                return s
            else:
                buf[0] = buf[0].replace
        print 'hi' + buf[0]
        """
        return last[0:-1]

def process_block(s, interesting, indentation, old, new):
    if not interesting:
        return s
    else:

        import parser
        body = s.replace(old, '', 1)
        return 'ASSERT' + body
            
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
