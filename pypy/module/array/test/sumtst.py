#!/usr/bin/python
from array import array

img=array(640*480);
def f():
    l=0
    i=0;
    while i<640*480:
        l+=img[i]
        i+=1
    return l


#for l in range(500): f()
print f()
