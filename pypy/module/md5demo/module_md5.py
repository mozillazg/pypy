from pypy.rlib import rmd5
from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.gateway import interp2app, ObjSpace, W_Root

from pypy.rlib.objectmodel import instantiate, we_are_translated
from pypy.translator.sepcomp import scimport, ImportExportComponent, export
from pypy.rlib.libffi import dlopen_global_persistent

class RMD5_interface(rmd5.RMD5):
    pass
class W_MD5(Wrappable):
    """
    A subclass of RMD5 that can be exposed to app-level.
    """
    _exported_ = True

    def __init__(self, space):
        self.space = space
        self._init()

    def update_w(self, string):
        self.update(string)

    @export
    def _init(self):
        return rmd5.RMD5._init(self)

    @export
    def digest(self):
        return rmd5.RMD5.digest(self)

    @export(str)
    def update(self, x):
        return rmd5.RMD5.update(self, x)

    @export(W_Root)
    def dostuff_w(self, w_arg):
        return w_arg

class W_MyMD5(W_MD5):
    def __init__(self, spacewrapper):
        self.spacewrapper = spacewrapper
        self._init()
    def digest(self):
        return W_MD5.digest(self) + "added string"

def module_init(spacewrapper, data):
    w_mymd5 = instantiate(W_MyMD5)
    if not we_are_translated():
        w_mymd5.space = spacewrapper.space
    w_mymd5.__init__(spacewrapper)
    w_mymd5.update(data)
    return w_mymd5

@export(SpaceWrapper, str, ret=W_Root, force_name="module_init")
def get_dynamic_object(foo):
    raise NotImplementedError

get_dynamic_object = scimport(get_dynamic_object, dynamic=True, forward_ref=True)


def dynamic_md5(space, initialdata=""):
    sw = SpaceWrapper(space)
    w_obj = get_dynamic_object(sw, initialdata)
    #w_obj = module_init(sw, initialdata)
    return w_obj
dynamic_md5.unwrap_spec = [ObjSpace, str]


