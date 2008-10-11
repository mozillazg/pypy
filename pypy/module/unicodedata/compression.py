
def build_compression_table(stringlist):
    # build compression code table
    BITS = 8
    codes = {}
    chars = {}
    # put all characters into code
    for value in stringlist:
        for char in value:
            chars.setdefault(char, len(chars))

    # fill code with larger strings
    for value in stringlist:
        start = 0
        for start in range(len(value)):
            for stop in range(start + 1, len(value)):
                codes[value[start:stop]] = codes.get(value[start:stop], 0) + 1

    # take most common strings
    s = [(freq, code) for (code, freq) in codes.iteritems() if len(code) > 1]
    s.sort()
    s.reverse()
    common =  chars.keys() + [code for freq, code in s[:2 ** BITS - len(chars)]]
    assert len(common) <= 2 ** BITS

    finalcodes = {}
    for code in common:
        assert code not in finalcodes
        finalcodes[code] = len(finalcodes)
    return finalcodes, common


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
