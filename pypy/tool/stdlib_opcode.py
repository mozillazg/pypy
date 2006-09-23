# load opcode.py as pythonopcode from our own lib
# This should handle missing local copy
def load_opcode():
    import py
    opcode_path = py.path.local(__file__).dirpath().dirpath().dirpath('lib-python/modified-2.4.1/opcode.py')
    execfile(str(opcode_path), globals())

    # __________ extra opcodes __________

    def def_op(name, op):
        opname[op] = name
        opmap[name] = op

    def_op('CALL_METHOD',        192)
    def_op('CALL_METHOD_VAR',    193)
    def_op('CALL_METHOD_KW',     194)
    def_op('CALL_METHOD_VAR_KW', 195)
    def_op('CALL_METHOD_FAST',   196)


load_opcode()
del load_opcode
