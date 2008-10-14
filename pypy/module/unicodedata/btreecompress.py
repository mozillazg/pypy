MINLIST  = 5 # minimum number of codepoints in range to make a list
MAXBLANK = 8 # max number of holes in a row in list range

classdef = """
class BTreeEntry(object):
    substring = ""
    codepoint = -1
    left = right = parent = None

    def __init__(self, substring, parent, left=False, codepoint=-1):
        self.substring = substring
        self.codepoint = codepoint
        self.parent = parent
        self.left = self.right = None
        if parent:
            if left:
                assert parent.left is None
                parent.left = self
            else:
                assert parent.right is None
                parent.right = self

def btree_lookup(name):
    charnode = _charnode_0_
    while charnode:
        if charnode.codepoint != -1 and name == charnode.substring:
            return charnode.codepoint
        if name.startswith(charnode.substring):
            name = name[len(charnode.substring):]
            charnode = charnode.left
        else:
            charnode = charnode.right
    raise KeyError, name
"""

def findranges(d):
    ranges = []
    for i in range(max(d)+1):
        if i in d:
            if not ranges:
                ranges.append((i,i))
                last = i
                continue
            if last + 1 == i:
                ranges[-1] = (ranges[-1][0], i)
            else:
                ranges.append((i,i))
            last = i
    return ranges

def collapse_ranges(ranges):
    collapsed = [ranges[0]]
    for i in range(1,len(ranges)):
        lows, lowe = collapsed[-1]
        highs, highe = ranges[i]
        if highs - lowe < MAXBLANK:
            collapsed[-1] = (lows, highe)
        else:
            collapsed.append(ranges[i])

    return collapsed

def build_compression_tree(outfile, ucdata):
    print >> outfile, classdef

    reversedict = {}
    rootnode = gen_compression_tree(
        outfile, ucdata.keys(), ucdata, reversedict)

    function = ["def lookup_charcode(code):",
                "    res = None"]
    ranges = collapse_ranges(findranges(reversedict))
    for low, high in ranges:
        if high - low <= MINLIST:
            for code in range(low, high + 1):
                if code in reversedict:
                    function.append(
                        "    if code == %d: res = %s" %
                        (code, reversedict[code]))
            continue

        function.append(
            "    if %d <= code <= %d: res = _charnames_%d[code-%d]" % (
            low, high, low, low))

        print >> outfile, "_charnames_%d = [" % (low,)
        for code in range(low, high + 1):
            print >> outfile, "%s," % (reversedict.get(code),)
        print >> outfile, "]\n"

    function.extend(["    if res is None: raise KeyError, code",
                     "    rstr = []",
                     "    left = res.left",
                     "    while res:",
                     "        if res.left is left:",
                     "            rstr.insert(0, res.substring)",
                     "        left = res",
                     "        res = res.parent",
                     "    return ''.join(rstr)",
                     "",
                     ])
    print >> outfile, '\n'.join(function)

def gen_compression_tree(outfile, stringlist, ucdata, reversedict, parent=None, parent_str="", left=False, counter=[0]):
    # Find "best" startstring
    if not stringlist:
        return None
    codes = {}
    for string in stringlist:
        for stop in range(1, len(string) + 1):
            codes[string[:stop]] = codes.get(string[:stop], 0) + 1
            
    s = [((freq), code) for (code, freq) in codes.iteritems()]            
    s.sort()
    if not s:
        return None
    newcode = s[-1][1]

    has_substring = []
    other_substring = []
    codepoint = None
    for string in stringlist:
        if string == newcode:
            codepoint = ucdata[parent_str+string]
        elif string.startswith(newcode):
            has_substring.append(string[len(newcode):])
        else:
            other_substring.append(string)

    btnode = "_charnode_%d_" % (counter[0],)
    args = '%r, %s' % (newcode, parent)
    if left:
        args += ', left=True'
    if codepoint:
        args += ', codepoint=%d' % (codepoint,)
        reversedict[codepoint] = btnode        

    print >> outfile, "%s = BTreeEntry(%s)" % (btnode, args)
    counter[0] += 1

    gen_compression_tree(
        outfile, has_substring, ucdata, reversedict,
        parent=btnode, parent_str=parent_str+newcode,
        left=True, counter=counter)
    gen_compression_tree(
        outfile, other_substring, ucdata, reversedict,
        parent=btnode, parent_str=parent_str,
        left=False, counter=counter)

    return btnode

def count_tree(tree):
    def subsum(tree, cset):
        if not tree:
            return 0, 0
        cset.add(tree.substring)
        lcount, ldepth = subsum(tree.left,cset)
        rcount, rdepth = subsum(tree.right,cset)
        return lcount+rcount+1, max(ldepth, rdepth) + 1

    cset = set()
    nodecount = subsum(tree, cset)
    strsize = sum(3*4 + len(s) for s in cset)
    nchars = sum(map(len, cset))

    return strsize, nodecount, nchars
