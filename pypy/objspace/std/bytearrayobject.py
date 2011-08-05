
def eq__Bytearray_Unicode(space, w_bytearray, w_other):
    return space.w_False

def eq__Unicode_Bytearray(space, w_other, w_bytearray):
    return space.w_False

def ne__Bytearray_Unicode(space, w_bytearray, w_other):
    return space.w_True

def ne__Unicode_Bytearray(space, w_other, w_bytearray):
    return space.w_True

def lt__Bytearray_Bytearray(space, w_bytearray1, w_bytearray2):
    data1 = w_bytearray1.data
    data2 = w_bytearray2.data
    ncmp = _min(len(data1), len(data2))
    # Search for the first index where items are different
    for p in range(ncmp):
        if data1[p] != data2[p]:
            return space.newbool(data1[p] < data2[p])
    # No more items to compare -- compare sizes
    return space.newbool(len(data1) < len(data2))

