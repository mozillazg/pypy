import re
import unittest

def parse(string):
    i = parser(string, 0)
    #print 'Returning ', (string[0:i], string[i+1:])
    return (string[0:i], string[i+1:])

def parser(string, i):
    #print string[i:]
    inDoubleQuotes = False
    inSingleQuotes = False
    for c in string[i:]:
        if string[i] == '(' and not (inSingleQuotes or inDoubleQuotes):
            #print "Calling", i+1
            i = parser(string, i+1)
        if string[i] == ')' and not (inSingleQuotes or inDoubleQuotes):
            #print "Returning", i+1
            return i+1
        if string[i] == '"' and not inSingleQuotes:
            if not inDoubleQuotes or not (string[i-1] == '\\' and string[i-2] !=
 '\\'):
                inDoubleQuotes = not inDoubleQuotes
        if string[i] == "'" and not inDoubleQuotes:
            if not inSingleQuotes or not (string[i-1] == '\\' and string[i-2] !=
 '\\'):
                inSingleQuotes = not inSingleQuotes

        if string[i] == ',' and not inDoubleQuotes and not inSingleQuotes:
            return i
        i += 1
    raise IndexError

pattern = re.compile(r'^(\s*)self\.assertEquals\((.*)')

def parseFile(filename):
    fp = file(filename, 'r')
    saved = ''
    for line in fp:
        line = saved + line
        match = pattern.search(line)
        if match:
            s = match.group(2)
            try:
                a,b = parse(s)
                b = b.rstrip()
                b = b[:-1]
                print '%sassert %s == %s' % (match.group(1), a, b)
                saved = ''
            except IndexError:
                saved = line.rstrip()
                #print "Saved: ", saved
        else:
            print line

class Testit(unittest.TestCase):
    def test(self):
        self.assertEquals(parse('111,9'), ('111','9'))
        self.assertEquals(parse('x","xx,yyy'), ('x","xx', 'yyy'))
        self.assertEquals(parse('xx' + "+\"z'z\"+" + 'x,yyy'),("xx+\"z'z\"+x", "yyy"))
        self.assertEquals(parse("x','xx,yyy"), ("x','xx", "yyy"))
        self.assertEquals(parse(r'''x"\","xx,yyy'''), (r'''x"\","xx''', 'yyy'))
        self.assertEquals(parse(r'''x'\','xx,yyy'''), (r'''x'\','xx''', 'yyy'))
        self.assertEquals(parse(r'''x",\\"xx,yyy'''), (r'''x",\\"xx''', 'yyy'))
        self.assertEquals(parse(r'''x',\\'xx,yyy'''), (r'''x',\\'xx''', 'yyy'))
        self.assertEquals(parse("(),7"), ("()", "7"))
        self.assertEquals(parse("(1+(3*2)),7"), ("(1+(3*2))", "7"))
        self.assertEquals(parse("('apa'+(3*2)),7"), ("('apa'+(3*2))", "7"))
        self.assertEquals(parse("('ap)a'+(3*2)),7"), ("('ap)a'+(3*2))", "7"))
        self.assertRaises(IndexError, parse, "('apa'+(3*2))7")
        self.assertRaises(IndexError, parse, "3 +")

if __name__ == '__main__':
    #unittest.main()
    parseFile('apa.py')
