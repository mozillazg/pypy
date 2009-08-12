import sys
import shutil

import py
from py.compat import subprocess
from pypy.config.config import Config
from pypy.translator.oosupport.genoo import GenOO
from pypy.translator.cli import conftest
from pypy.translator.cli.avm1gen import AVM1Gen

class GenAVM1(GenOO):
    
    ConstantGenerator = constant.AVM1ConstGenerator

    def __init__(self, tmpdir, translator, entrypoint, config=None, exctrans=False):
        GenOO.__init__(self, tmpdir, translator, entrypoint, config, exctrans)
        self.assembly_name = entrypoint.get_name()
        self.const_stat = str(tmpdir.join('const_stat'))
            
    def create_assembler(self):
        return AVM1Gen()
