
"""
The low-level implementation of termios module
note that this module should only be imported when
termios module is there
"""

import termios
from pypy.rpython.lltypesystem import rffi
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.extfunc import register_external
from pypy.rlib.rarithmetic import intmask
from pypy.rpython.extregistry import ExtRegistryEntry
from pypy.annotation import model as annmodel
from pypy.rpython import rclass

# XXX is this portable? well.. not at all, ideally
# I would like to have NCCS = CLaterConstant(NCCS)
TCFLAG_T = rffi.UINT
CC_T = rffi.UCHAR
NCCS = 32
SPEED_T = rffi.UINT

includes = ['termios.h', 'unistd.h']

TERMIOSP = rffi.CStruct('termios', ('c_iflag', TCFLAG_T), ('c_oflag', TCFLAG_T),
                        ('c_cflag', TCFLAG_T), ('c_lflag', TCFLAG_T),
                        ('c_cc', lltype.FixedSizeArray(CC_T, NCCS)))

c_tcgetattr = rffi.llexternal('tcgetattr', [lltype.Signed, TERMIOSP],
                              lltype.Signed, includes=includes)
c_cfgetispeed = rffi.llexternal('cfgetispeed', [TERMIOSP], SPEED_T,
                                includes=includes)
c_cfgetospeed = rffi.llexternal('cfgetospeed', [TERMIOSP], SPEED_T,
                                includes=includes)

class termios_error(termios.error):
    def __init__(self, num, msg):
        self.args = (num, msg)

def tcgetattr_llimpl(fd):
    c_struct = lltype.malloc(TERMIOSP.TO, flavor='raw')
    error = c_tcgetattr(fd, c_struct)
    if error == -1:
        lltype.free(c_struct, flavor='raw')
        raise termios_error(error, 'tcgetattr failed')
    cc = [chr(c_struct.c_c_cc[i]) for i in range(NCCS)]
    ispeed = c_cfgetispeed(c_struct)
    ospeed = c_cfgetospeed(c_struct)
    result = (intmask(c_struct.c_c_iflag), intmask(c_struct.c_c_oflag),
              intmask(c_struct.c_c_cflag), intmask(c_struct.c_c_lflag),
              intmask(ispeed), intmask(ospeed), cc)
    lltype.free(c_struct, flavor='raw')
    return result

register_external(termios.tcgetattr, [int], (int, int, int, int, int, int, [str]),
                  llimpl=tcgetattr_llimpl, export_name='termios.tcgetattr')

#def tcsetattr_llimpl(fd
