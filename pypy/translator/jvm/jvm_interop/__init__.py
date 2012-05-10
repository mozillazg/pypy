from annmodel import *  # register annotator entries
from ootypemodel import *
from rtypemodel import *

def add_registry_entries():
    """
    The entries are added by executing the above imports.
    This function is here to avoid "useless" imports of jvm_interop.
    """
    pass
