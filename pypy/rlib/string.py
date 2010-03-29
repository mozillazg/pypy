def split(value, by, maxsplit):
    bylen = len(by)
    if bylen == 0:
        raise ValueError("empty separator")

    res = []
    start = 0
    while maxsplit != 0:
        next = value.find(by, start)
        if next < 0:
            break
        res.append(value[start:next])
        start = next + bylen
        maxsplit -= 1   # NB. if it's already < 0, it stays < 0

    res.append(value[start:len(value)])
    return res
