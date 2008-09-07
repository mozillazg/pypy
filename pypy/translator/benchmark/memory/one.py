
import gc

class A(object):
    pass

class B(object):
    def __init__(self):
        self.a = [1,2,3]
        self.b = "xyz"

x = [(A(), B()) for i in range(100000)]
gc.collect()

while 1:
    pass
#j = 0
#while j < 20:
#    x = [(A(), B()) for i in range(100000)]
#    del x
#    gc.collect()
#    j += 1
