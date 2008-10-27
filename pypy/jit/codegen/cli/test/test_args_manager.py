import py
from pypy.jit.codegen.cli.args_manager import BaseArgsManager

class MyArgsManager(BaseArgsManager):

    def stelem(self, meth, i, gv_arg, field, elemtype):
        gv_arg.load(meth)
        meth.operations.append(('stelem', field, i))

    def ldelem(self, meth, i, field, elemtype):
        meth.operations.append(('ldelem', field, i))

    def _normalize_type(self, clitype):
        if clitype == 'uint':
            return 'int'
        return clitype

    def _get_array(self, clitype):
        return clitype+'s', clitype


class FakeMethod:

    def __init__(self):
        self.operations = []
        self.gv_inputargs = FakeGenVar('InputArgs')

class FakeGenVar:

    def __init__(self, clitype):
        self.clitype = clitype

    def getCliType(self):
        return self.clitype

    def store(self, meth):
        meth.operations.append(('store', self))

    def load(self, meth):
        meth.operations.append(('load', self))


def test_copy_to_inputargs():
    meth = FakeMethod()
    gv_inputargs = meth.gv_inputargs
    gv_x = FakeGenVar('int')
    gv_y = FakeGenVar('float')
    gv_z = FakeGenVar('uint')
    args_gv = [gv_x, gv_y, gv_z]
    
    m = MyArgsManager()
    m.copy_to_inputargs(meth, args_gv)

    assert meth.operations == [
        ('load', gv_x),
        ('stelem', 'ints', 0),
        ('load', gv_z),
        ('stelem', 'ints', 1),
        ('load', gv_y),
        ('stelem', 'floats', 0),
        ]

def test_copy_from_inputargs():
    meth = FakeMethod()
    gv_inputargs = meth.gv_inputargs
    gv_x = FakeGenVar('int')
    gv_y = FakeGenVar('float')
    gv_z = FakeGenVar('uint')
    args_gv = [gv_x, gv_y, gv_z]

    m = MyArgsManager()
    m.copy_from_inputargs(meth, args_gv)

    assert meth.operations == [
        ('ldelem', 'ints', 0),
        ('store', gv_x),
        ('ldelem', 'ints', 1),
        ('store', gv_z),
        ('ldelem', 'floats', 0),
        ('store', gv_y),
        ]
