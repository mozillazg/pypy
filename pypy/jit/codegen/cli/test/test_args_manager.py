import py
from pypy.jit.codegen.cli.args_manager import BaseArgsManager

class MyArgsManager(BaseArgsManager):

    def _init_types(self):
        self.clitype_InputArgs = 'InputArgs'
        self.clitype_Void = 'Void'
        self.clitype_Pair = 'Pair'

    def _make_generic_type(self, clitype, paramtypes):
        return clitype, paramtypes

    def _store_by_index(self, meth, gv_arg, i):
        meth.operations.append(('store_arg', gv_arg, i))
    
    def _load_by_index(self, meth, i):
        meth.operations.append(('load_arg', i))

class FakeMethod:

    def __init__(self):
        self.operations = []

class FakeGenVar:

    def __init__(self, clitype):
        self.clitype = clitype

    def getCliType(self):
        return self.clitype

    def store(self, meth):
        meth.operations.append(('store', self))


def test_register_types():
    m = MyArgsManager()
    assert m.is_open()
    m.register_types(['int', 'float', 'int'])
    assert m.type_counter['int'] == 2
    assert m.type_counter['float'] == 1

    m.register_types(['int', 'int', 'int'])
    assert m.type_counter['int'] == 3
    assert m.type_counter['float'] == 1

def test_close():
    m = MyArgsManager()
    m.register_types(['int', 'float', 'int'])
    m.close()
    assert not m.is_open()
    # XXX: this test depend on dictionary order :-/
    assert m.getCliType() == (
        'InputArgs', [
            ('Pair', [
                    'int', ('Pair', [
                            'int', ('Pair', [
                                    'float', 'Void'
                                    ])
                            ])
                    ])
            ])
    
    assert m.type_index['int'] == 0
    assert m.type_index['float'] == 2

def test__get_indexes():
    py.test.skip('fixme')
    m = MyArgsManager()
    m.register_types(['int', 'float', 'int'])
    m.close()
    indexes = m._get_indexes(['int', 'float', 'int'])
    assert indexes == [0, 1, 2]

def test_copy_to_inputargs():
    meth = FakeMethod()
    gv_x = FakeGenVar('int')
    gv_y = FakeGenVar('int')
    args_gv = [gv_x, gv_y]
    
    m = MyArgsManager()
    m.register(args_gv)
    m.close()
    m.copy_to_inputargs(meth, args_gv)

    assert meth.operations == [
        ('store_arg', gv_x, 0),
        ('store_arg', gv_y, 1)
        ]

def test_copy_from_inputargs():
    meth = FakeMethod()
    gv_x = FakeGenVar('int')
    gv_y = FakeGenVar('int')
    args_gv = [gv_x, gv_y]

    m = MyArgsManager()
    m.register(args_gv)
    m.close()
    m.copy_from_inputargs(meth, args_gv)

    assert meth.operations == [
        ('load_arg', 0),
        ('store', gv_x),
        ('load_arg', 1),
        ('store', gv_y)
        ]
