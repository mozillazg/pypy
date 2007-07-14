import py
from pypy.tool.ansi_print import ansi_log
log = py.log.Producer("flex")
py.log.setconsumer("flex", ansi_log)
