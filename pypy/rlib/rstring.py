
""" String builder interface
"""

INIT_SIZE = 100 # XXX tweak

class StringBuilder(object):
    def __init__(self, init_size=INIT_SIZE):
        self.l = []

    def append(self, s):
        self.l.append(s)

    def append_char(self, c):
        self.l.append(c)

    def build(self):
        return "".join(self.l)

