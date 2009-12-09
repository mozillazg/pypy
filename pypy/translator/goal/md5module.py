from pypy.translator.sepcomp import scimport, export, ImportExportComponent
from pypy.module.md5demo.interface import MD5Interface


class MD5Inherited(MD5Interface):
    def __init__(self):
        self.argument_cache = []

    def update(self, x):
        # keeps all strings that were fed into this hash object
        self.argument_cache.append(x)
        return MD5Interface.update(self, x)

    def digest(self):
        return MD5Interface.digest(self) + "POSTF3"


@export(ret=MD5Interface, force_name="module_init")
def module_init():
    return MD5Inherited()

ImportExportComponent("md5module", locals())
