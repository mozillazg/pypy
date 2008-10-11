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
            for stop in range(1, len(string) + 1):
                if string[:stop] not in finalcodes:
                    codes[string[:stop]] = codes.get(string[:stop], 0) + 1

        s = [((freq - 1) * (len(code) - 1), code) for (code, freq) in codes.iteritems()]
        s.sort()
        if not s:
            break
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
    finalcodes.sort(key=len)
    finalcodes.reverse()

    return finalcodes

def compress(codelist, s):
    result = ""
    while s:
        for i in range(len(codelist)):
            code = codelist[i]
            if s.startswith(code):
                result += chr(i)
                s = s[len(code):]
                break
        else:
            assert 0, "bogus codelist"
    return result

def uncompress(codelist, s):
    result = []
    for sym in s:
        result.append(codelist[ord(sym)])
    return "".join(result)
