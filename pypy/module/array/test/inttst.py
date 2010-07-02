#!/usr/bin/python
from time import time

from array import array
#img=array('B',(0,)*640*480);
#intimg=array('I',(0,)*640*480);
img=array(640*480);
intimg=array(640*480);

def f():
    l=0
    for i in xrange(640,640*480):
        l+=img[i]
        intimg[i]=intimg[i-640]+l


start=time()
for l in range(500): f()
print time()-start
