from pypy.translator.avm2.sudanpython import export

@export(int, int)
def sum(a, b):
    return a+b
