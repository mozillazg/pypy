import cppyy

import time
import cppyy
lib = cppyy.load_lib("example01Dict.so")
cls = lib.type_byname("example01")
inst = cls.construct(-17)

t1 = time.time()
res = 0
for i in range(1000000):
    res += inst.invoke("add", i)
t2 = time.time()
print t2 - t1
