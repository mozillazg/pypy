from pypy.interpreter.lazymodule import LazyModule
    
class Module(LazyModule):
    appleveldefs = {
    }
    interpleveldefs = {
        'lookup'          : 'functions.lookup',
        'name'            : 'functions.name',
        'decimal'         : 'functions.decimal',
        'digit'           : 'functions.digit',
        'numeric'         : 'functions.numeric',
        'category'        : 'functions.category',
        'bidirectional'   : 'functions.bidirectional',
        'combining'       : 'functions.combining',
        'mirrored'        : 'functions.mirrored',
        'decomposition'   : 'functions.decomposition',
        'normalize'       : 'functions.normalize',
        'unidata_version' : 'space.wrap(unicodedb.version)',
        '__doc__'         : "space.wrap('unicode character database')",
    }
