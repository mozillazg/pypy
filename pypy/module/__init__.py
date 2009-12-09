# empty
from pypy.module.md5demo import interp_md5
from pypy.translator.sepcomp import scimport, ImportExportComponent, export

ImportExportComponent("md5demo", interp_md5)
