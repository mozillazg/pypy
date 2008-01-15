# Package initialisation
from pypy.interpreter.mixedmodule import MixedModule

import boxing_rules # with side effects

class Module(MixedModule):
    """CLR module"""

    appleveldefs = {
        'dotnetimporter': 'app_importer.importer'
        }
    
    interpleveldefs = {
        '_CliObject_internal': 'interp_clr.W_CliObject',
        'call_staticmethod': 'interp_clr.call_staticmethod',
        'load_cli_class': 'interp_clr.load_cli_class',
        'get_extra_type_info': 'interp_clr.get_extra_type_info',
        'isDotNetType': 'interp_clr.isDotNetType',
        'load_assembly': 'interp_clr.load_assembly',
        'list_of_loadedAssemblies': 'interp_clr.list_of_loadedAssemblies',
    }

    def setup_after_space_initialization(self):
        self.space.appexec([self], """(clr_module):
            import sys
            sys.meta_path.append(clr_module.dotnetimporter())
            """)
