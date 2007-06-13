"""XXX temporary integration hack"""

import autopath, os

# make pypy.translator.tool.pygame behave like a package whose content
# is in the dotviewer/ subdirectory
__path__ = [os.path.join(autopath.this_dir, 'dotviewer')]
