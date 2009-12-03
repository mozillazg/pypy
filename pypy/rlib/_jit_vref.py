from pypy.annotation import model as annmodel


class SomeVRef(annmodel.SomeObject):

    def __init__(self, s_instance):
        self.s_instance = s_instance

    def simple_call(self):
        return self.s_instance
