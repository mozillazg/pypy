from pypy.rlib import rmd5
from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.gateway import interp2app, ObjSpace, W_Root

from pypy.rlib.objectmodel import instantiate, we_are_translated
from pypy.translator.sepcomp import scimport, ImportExportComponent, export
from pypy.rlib.libffi import dlopen_global_persistent


class RMD5Interface(rmd5.RMD5):
    _exported_ = True
    @export
    def _init(self):
        rmd5.RMD5._init(self)
        return 1

    @export
    def digest(self):
        return rmd5.RMD5.digest(self)

    @export(str)
    def update(self, x):
        return rmd5.RMD5.update(self, x)


class W_MD5(Wrappable):
    """
    A subclass of RMD5 that can be exposed to app-level.
    """

    def __init__(self, space, md5obj):
        self.space = space
        self.md5obj = md5obj
        md5obj._init()

    def update_w(self, string):
        self.md5obj.update(string)

    def digest_w(self):
        return self.space.wrap(self.md5obj.digest())

    def hexdigest_w(self):
        return self.space.wrap(self.md5obj.hexdigest())


def W_MD5___new__(space, w_subtype, initialdata=''):
    """
    Create a new md5 object and call its initializer.
    """
    a = RMD5Interface() # hack
    w_md5 = space.allocate_instance(W_MD5, w_subtype)
    md5 = space.interp_w(W_MD5, w_md5)
    W_MD5.__init__(md5, space, module_init())
    md5.md5obj.update(initialdata)
    return w_md5

class MyRMD5(RMD5Interface):
    def digest(self):
        return RMD5Interface.digest(self) + "added string"

def module_init():
    return get_dynamic_object()
    #return MyRMD5()

@export(ret=RMD5Interface, force_name="module_init")
def get_dynamic_object(foo):
    raise NotImplementedError

get_dynamic_object = scimport(get_dynamic_object, dynamic=True, forward_ref=True)



def load_module(space):
    dlopen_global_persistent("/tmp/testmodule.so")
    return space.wrap(None)
load_module.unwrap_spec = [ObjSpace]

W_MD5.typedef = TypeDef(
    'MD5Type',
    __new__   = interp2app(W_MD5___new__, unwrap_spec=[ObjSpace, W_Root,
                                                       'bufferstr']),
    update    = interp2app(W_MD5.update_w, unwrap_spec=['self', 'bufferstr']),
    digest    = interp2app(W_MD5.digest_w, unwrap_spec=['self']),
    hexdigest = interp2app(W_MD5.hexdigest_w, unwrap_spec=['self']),
    __doc__   = """md5(arg) -> return new md5 object.

If arg is present, the method call update(arg) is made.""")
