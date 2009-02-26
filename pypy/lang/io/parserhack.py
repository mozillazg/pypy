import py
import os

implicit = "implicit"

io_file = py.magic.autopath().dirpath().join("parserhack.io")

class Ast(object):
    def __init__(self, receiver, name, arguments = None):
        self.receiver = receiver
        self.name = name
        if arguments is None:
            arguments = []
        self.arguments = arguments
        
    def __repr__(self):
        return "Ast(%r, %r, %r)" % (self.receiver, self.name, self.arguments)

    def __eq__(self, other):
        return (self.__class__ is other.__class__ and 
                self.__dict__ == other.__dict__)
        
    def __ne__(self, other):
        return not self == other
        
def parse(input):
    child_in, child_out_err = os.popen4("osxvm %s" % io_file)
    child_in.write(input)
    child_in.close()
    s = child_out_err.read().strip()
    return eval(s)
    