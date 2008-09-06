
class A(object):
    pass

class B(object):
    def __init__(self):
        self.a = [1,2,3]
        self.b = "xyz"

j = 0
while j < 20:
    x = [(A(), B()) for i in range(100000)]
    del x
    j += 1
