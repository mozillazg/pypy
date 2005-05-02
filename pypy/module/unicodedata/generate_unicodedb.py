#!/usr/bin/env python

import sys
import __future__

def printDict(outfile, name, dictionary):
    keys = dictionary.keys()
    keys.sort()
    print >> outfile, name, '= {'
    for key in keys:
        print >>outfile, '    %r : %r,' % (key, dictionary[key])
    print  >>outfile, '}'
    
def generate_unicodedb(unidata_version, infile, outfile):
    decimal = {}
    digit = {}
    number = {}
    uppercase = {}
    lowercase = {}
    titlecase = {}
    category = {}
    name = {}
    combining = {}
    bidir = {}
    mirrored = {}

    decomp = {}

    table = {}
    for line in infile:
        line = line.split('#', 1)[0].strip()
        if not line:
            continue
        data = [ v.strip() for v in line.split(';') ]
        code = data[0] = int(data[0], 16)
        table[code] = data

    # Expand named ranges
    field = None
    for i in range(0, 0x110000):
        s = table.get(i)
        if s:
            if s[1][-8:] == ", First>":
                field = s[:]
                field[1] = s[1][:-8]
                s[1] = s[1][:-8] + '-%4X'%s[0]
            elif s[1][-7:] == ", Last>":
                s[1] = s[1][:-7] + '-%4X'%s[0]
                field = None
        elif field:
            s = field[:]
            s[0] = i
            s[1] = s[1] + '-%4X'%s[0]
            table[i] = s

    for (code, _name, cat, _combine, _bidir, _decomp,
         _decimal, _digit, _number, _mirrored, unicode1_name, comment,
         _uppercase, _lowercase, _titlecase) in table.itervalues():
        if cat != 'Cn':
            category[code] = cat

        name[code] = _name
        if _combine:
            combine = int(_combine)
            if combine != 0:
                combining[code] = combine

        if _decimal:
            decimal[code] = int(_decimal)
        if _digit:
            d = digit[code] = int(_digit)
        if _number:
            number[code] = float(eval(compile(_number, '-', 'eval', __future__.CO_FUTURE_DIVISION, 1)))

        if _uppercase:
            uppercase[code] = int(_uppercase, 16)
        if _lowercase:
            lowercase[code] = int(_lowercase, 16)
        if _titlecase:
            titlecase[code] = int(_titlecase, 16)

        if _mirrored == 'Y':
            mirrored[code] = 1

        if _bidir:
            bidir[code] = _bidir

        #if _decomp:
        #    raise Exception

    codeByName = {}
    duplicateNames = {}
    for k, v in name.iteritems():
        if duplicateNames.has_key(k):
            continue
        if codeByName.has_key(k):
            duplicateNames[k] = 1
            del codeByName[k]
            continue
        codeByName[k] = v

    print >> outfile, 'version = %r'%unidata_version
    print >> outfile
    printDict(outfile, 'charnameByCode', name)
    print >> outfile
    printDict(outfile,'charcodeByName', codeByName)
    print >> outfile
    printDict(outfile, 'decimalValue', decimal)
    print >> outfile
    printDict(outfile, 'digitValue', digit)
    print >> outfile
    printDict(outfile, 'numericValue', number)
    print >> outfile
    printDict(outfile, 'category', category)
    print >> outfile
    printDict(outfile, 'bidirectional', bidir)
    print >> outfile
    printDict(outfile, 'combining', combining)
    print >> outfile
    printDict(outfile, 'mirrored', mirrored)
    print >> outfile
    printDict(outfile, 'decomposition', decomp)
    print >> outfile
    printDict(outfile, 'uppercase', uppercase)
    print >> outfile
    printDict(outfile, 'lowercase', lowercase)
    print >> outfile
    printDict(outfile, 'titlecase', titlecase)
    print >> outfile

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
    
    print >> outfile, '# UNICODE CHARACTER DATABASE'
    print >> outfile, '# This ficle was genrated with the command:'
    print >> outfile, '#   ', ' '.join(sys.argv)
    print >> outfile

    generate_unicodedb(unidata_version, infile, outfile)
