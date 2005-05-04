#!/usr/bin/env python
import sys

class Unicodechar(object):
    __slots__ = '''code name category combining bidirectional
    decomposition decomposition_tag decimal digit numeric
    mirrored upper lower title'''.split()
    def __init__(self, data):
        if not data[1] or data[1][0] == '<' and data[1][-1] == '>':
            self.name = None
        else:
            self.name = data[1]
        self.category = data[2]
        self.combining = 0
        if data[3]:
            self.combining = int(data[3])
        self.bidirectional = data[4]
        self.decomposition = None
        self.decomposition_tag = None
        if data[5]:
            if data[5][0] == '<':
                tag, value = data[5].split(None, 1)
            else:
                tag = '<canonical>'
                value = data[5]
            self.decomposition_tag = tag[1:-1]
            self.decomposition = [int(v, 16) for v in value.split()]
                
        self.decimal = None
        if data[6]:
            self.decimal = int(data[6])
        self.digit = None
        if data[7]:
            self.digit = int(data[7])
        self.numeric = None
        if data[8]:
            try:
                numerator, denomenator = data[8].split('/')
                self.numeric = float(numerator) / float(denomenator)
            except ValueError:
                self.numeric = float(data[8])
        self.mirrored = (data[9] == 'Y')
        if data[12]:
            self.upper = int(data[12], 16)
        self.lower = None
        if data[13]:
            self.lower = int(data[13], 16) 
        self.title = None
        if data[14]:
            self.title = int(data[14], 16)

    def isspace(self):
        return (self.category == 'Zs' or
                self.bidirectional in ('WS', 'B' or 'S'))
    
def read_unicodedata(infile):
    rangeFirst = {}
    rangeLast = {}
    table = [Unicodechar(['0000', None, 'Cn'] + [''] * 12)] * (sys.maxunicode + 1)
    for line in infile:
        line = line.split('#', 1)[0].strip()
        if not line:
            continue
        data = [ v.strip() for v in line.split(';') ]
        if data[1].endswith(', First>'):
            code = int(data[0], 16)
            name = data[1][1:-len(', First>')]
            rangeFirst[name] = (code, data)
            continue
        if data[1].endswith(', Last>'):
            code = int(data[0], 16)
            rangeLast[name]  = code
            continue
        code = int(data[0], 16)
        u = Unicodechar(data)
        table[code] = u

    # Expand ranges
    for name, (start, data) in rangeFirst.iteritems():
        end = rangeLast[name]
        unichar = Unicodechar(['0000', None] + data[2:])
        for code in range(start, end + 1):
            table[code] = unichar

    return table

def writeDict(outfile, name, dictionary):
    print >> outfile, '%s = {' % name
    keys = dictionary.keys()
    keys.sort()
    for key in keys:
        print >> outfile, '%r: %r,'%(key, dictionary[key])
    print >> outfile, '}'
    print >> outfile

def writeCategory(outfile, table, name, categoryNames):
    print >> outfile, '_%s_names = %r' % (name, categoryNames)
    print >> outfile, '_%s = "".join([' % name
    for i in range(0, len(table), 64):
        result = []
        for char in table[i:i + 64]:
            result.append(chr(categoryNames.index(getattr(char, name)) + 0x20))
        print >> outfile, '    %r,' % ''.join(result)
    print >> outfile, '])'
    print >> outfile, '''
def %s(code):
    return _%s_names[ord(_%s[code]) & 0x1f]    

'''%(name, name, name)

def writeUnicodedata(version, table, outfile):
    # Version
    print >> outfile, 'version = %r' % version
    print >> outfile
    # Character names
    print >> outfile, '_charnames = {'
    for code in range(len(table)):
        if table[code].name:
            print >> outfile, '%r: %r,'%(code, table[code].name)
    print >> outfile, '''}
    
_code_by_name = dict(zip(_charnames.itervalues(), _charnames.iterkeys()))

def lookup(name):
    return _code_by_name[name]

def name(code):
    return _charnames[code]
'''
    # Categories
    categories = {}
    bidirs = {}
    for char in table:
        categories[char.category] = 1
        bidirs[char.bidirectional] = 1
    category_names = categories.keys()
    category_names.sort()
    if len(category_names) > 32:
        raise RuntimeError('Too many general categories defined.')
    bidirectional_names = bidirs.keys()
    bidirectional_names.sort()
    if len(bidirectional_names) > 32:
        raise RuntimeError('Too many bidirectional categories defined.')

    writeCategory(outfile, table, 'category', category_names)
    writeCategory(outfile, table, 'bidirectional', bidirectional_names)
    print >> outfile, '''
def isspace(code):
    return category(code) == "Zs" or bidirectional(code) in ("WS", "B", "S")
def islower(code):
    return category(code) == "Ll"
def isupper(code):
    return category(code) == "Lu"
def istitle(code):
    return category(code) == "Lt"
def isalpha(code):
    return category(code) in ("Lm", "Lt", "Lu", "Ll", "Lo")
def islinebreak(code):
    return category(code) == "Zl" or bidirectional(code) == "B"
'''
    
    # Numeric characters
    decimal = {}
    digit = {}
    numeric = {}
    for code in range(len(table)):
        if table[code].decimal is not None:
            decimal[code] = table[code].decimal
        if table[code].digit is not None:
            digit[code] = table[code].digit
        if table[code].numeric is not None:
            numeric[code] = table[code].numeric
            
    writeDict(outfile, '_decimal', decimal)
    writeDict(outfile, '_digit', digit)
    writeDict(outfile, '_numeric', numeric)
    print >> outfile, '''
def decimal(code):
    return _decimal[code]

def isdecimal(code):
    return _decimal.has_key(code)

def digit(code):
    return _digit[code]

def isdigit(code):
    return _digit.has_key(code)

def numeric(code):
    return _numeric[code]

def isnumeric(code):
    return _numeric.has_key(code)

'''
    # Combining
    combining = {}
    for code in range(len(table)):
        if table[code].combining:
            combining[code] = table[code].combining
    writeDict(outfile, '_combining', combining)
    print >> outfile, '''
def combining(code):
    return _combining.get(code, 0)

'''
    # Mirrored
    mirrored = dict([(code, 1) for char in table
                      if char.mirrored])
    mirrored = {}
    for code in range(len(table)):
        if table[code].mirrored:
            mirrored[code] = 1
    writeDict(outfile, '_mirrored', mirrored)
    print >> outfile, '''
def mirrored(code):
    return _mirrored.get(code, 0)

'''

if __name__ == '__main__':
    import getopt, re
    infile = None
    outfile = sys.stdout
    unidata_version = None
    options, args = getopt.getopt(sys.argv[1:], 'o:v:',
                                  ('output=', 'version='))
    for opt, val in options:
        if opt in ('-o', '--output'):
            outfile = open(val, 'w')
        if opt in ('-v', '--version'):
            unidata_version = val

    if len(args) != 2:
        raise RuntimeError('Usage: %s [-o outfile] [-v version] UnicodeDataFile CompositionExclutionsFile')
    
    infilename = args[0]
    infile = open(infilename, 'r')
    if unidata_version is None:
        m = re.search(r'-([0-9]+\.)+', infilename)
        if m:
            unidata_version = infilename[m.start() + 1:m.end() - 1]
    
    if unidata_version is None:
        raise ValueError('No version specified')

    table = read_unicodedata(infile)
    print >> outfile, '# UNICODE CHARACTER DATABASE'
    print >> outfile, '# This file was genrated with the command:'
    print >> outfile, '#    ', ' '.join(sys.argv)
    print >> outfile
    writeUnicodedata(unidata_version, table, outfile)
