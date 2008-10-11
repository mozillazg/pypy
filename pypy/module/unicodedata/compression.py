BITS = 8

def build_compression_table(stringlist):
    chars = {}
    # put all used characters
    for value in stringlist:
        for char in value:
            chars.setdefault(char, len(chars))

    finalcodes = chars.keys()

    stringlist = [s for s in stringlist if len(s) > 1]
    # fill code with larger strings
    while len(finalcodes) < 2 ** BITS and stringlist:
        codes = {}
        for string in stringlist:
            for stop in range(1, len(string)):
                codes[string[:stop]] = codes.get(string[:stop], 0) + 1

        s = [(freq * (len(code) - 1), code) for (code, freq) in codes.iteritems()]
        s.sort()
        newcode = s[-1][1]
        print repr(newcode)
        newstringlist = []
        for string in stringlist:
            if string.startswith(newcode):
                newstring = string[len(newcode):]
                if len(newstring) > 1:
                    newstringlist.append(newstring)
            else:
                newstringlist.append(string)
        assert newstringlist != stringlist
        stringlist = newstringlist
        finalcodes.append(newcode)

    codetable = {}
    for code in finalcodes:
        codetable[code] = len(codetable)
    return codetable, finalcodes

def compress(codetable, s):
    start = 0
    result = ""
    while start < len(s):
        stop = start + 1
        while stop <= len(s):
            if s[start:stop + 1] not in codetable:
                result += chr(codetable[s[start:stop]])
                break
            else:
                stop += 1
        else:
            # true only for last symbol
            result += chr(codetable[s[start:]])
        start = stop
    
    return result

def uncompress(codelist, s):
    result = []
    for sym in s:
        result.append(codelist[ord(sym)])
    return "".join(result)
