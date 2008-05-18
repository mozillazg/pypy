

def str_replace(input, sub, by, maxsplit=-1):
    if maxsplit == 0:
        return input

    #print "from replace, input: %s, sub: %s, by: %s" % (input, sub, by)

    if not sub:
        upper = len(input)
        if maxsplit > 0 and maxsplit < upper + 2:
            upper = maxsplit - 1
            assert upper >= 0
        substrings = [""]
        for i in range(upper):
            c = input[i]
            substrings.append(c)
        substrings.append(input[upper:])
        return by.join(substrings)
    startidx = 0
    substrings = []
    foundidx = input.find(sub, startidx)
    while foundidx >= 0 and maxsplit != 0:
        substrings.append(input[startidx:foundidx])
        startidx = foundidx + len(sub)        
        foundidx = input.find(sub, startidx)
        maxsplit = maxsplit - 1
    substrings.append(input[startidx:])
    return by.join(substrings)