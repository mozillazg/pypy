from pypy.translator.flex.modules.flex import *

class Foo:
    def __init__(self, msg):
        self.msg = msg
    
def flash_main(a=1):
    f = Foo("hello")
    for x in [1,2,3]:
        abutton = Button()
        abutton.label = "I'm button :" + str(x)
        addChild(abutton)
    return f.msg

