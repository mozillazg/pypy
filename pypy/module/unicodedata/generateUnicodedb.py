#!/usr/bin/env python

import sys
import __future__

unidata_version = sys.argv[1]

decimal = {}
digit = {}
number = {}
uppercase = {}
lowercase = {}
titlecase = {}
category = {}
decomp = {}
bidir = {}
combining = {}
mirrored = {}
decomp = {}
name = {}

def printDict(name, dictionary):
    keys = dictionary.keys()
    keys.sort()
    print name, '= {'
    for key in keys:
        print '    %r : %r,' % (key, dictionary[key])
    print '}'
    
for line in sys.stdin:
    line = line.split('#', 1)[0].strip()
    if not line:
        continue
    (code, _name, cat, _combine, _bidir, _decomp,
     _decimal, _digit, _number, _mirrord, unicode1_name, comment,
     _uppercase, _lowercase, _titlecase) =  [ v.strip() for v in line.split(';') ]
    code = int(code, 16)
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


print '# UNICODE CHARACTER DATABASE'
print
print 'version = %r'%unidata_version
print
printDict('charnameByCode', name)
print
printDict('charcodeByName', dict([(v, k) for k, v in name.iteritems()]))
print
printDict('decimalValue', decimal)
print
printDict('digitValue', digit)
print
printDict('numericValue', number)
print
printDict('category', category)
print
printDict('bidirectional', bidir)
print
printDict('combining', combining)
print
printDict('mirrored', mirrored)
print
printDict('decomposition', decomp)
print
printDict('uppercase', uppercase)
print
printDict('lowercase', lowercase)
print
printDict('titlecase', titlecase)
print

