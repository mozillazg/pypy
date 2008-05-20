import ctypes as _ctypes

class _handle:
    def __init__(self, handle):
        self.handle = handle

    def __int__(self):
        return self.handle

    def Detach(self):
        handle, self.handle = self.handle, None
        return handle

    def Close(self):
        _CloseHandle = _ctypes.WinDLL('kernel32').CloseHandle
        _CloseHandle.argtypes = [_ctypes.c_int]
        _CloseHandle.restype = _ctypes.c_int

        if self.handle not in (-1, None):
            _CloseHandle(self.handle)
            self.handle = None

def CreatePipe(attributes, size):
    _CreatePipe = _ctypes.WinDLL('kernel32').CreatePipe
    _CreatePipe.argtypes = [_ctypes.POINTER(_ctypes.c_int), _ctypes.POINTER(_ctypes.c_int),
                            _ctypes.c_void_p, _ctypes.c_int]
    _CreatePipe.restype = _ctypes.c_int

    read = _ctypes.c_int()
    write = _ctypes.c_int()

    res = _CreatePipe(_ctypes.byref(read), _ctypes.byref(write), None, size)

    if not res:
        raise WindowsError("Error")

    return _handle(read.value), _handle(write.value)

def GetCurrentProcess():
    _GetCurrentProcess = _ctypes.WinDLL('kernel32').GetCurrentProcess
    _GetCurrentProcess.argtypes = []
    _GetCurrentProcess.restype = _ctypes.c_int

    return _handle(_GetCurrentProcess())


def DuplicateHandle(source_process, source, target_process, access, inherit, options=0):
    _DuplicateHandle = _ctypes.WinDLL('kernel32').DuplicateHandle
    _DuplicateHandle.argtypes = [_ctypes.c_int, _ctypes.c_int, _ctypes.c_int,
                                 _ctypes.POINTER(_ctypes.c_int),
                                 _ctypes.c_int, _ctypes.c_int, _ctypes.c_int]
    _DuplicateHandle.restype = _ctypes.c_int
    
    target = _ctypes.c_int()

    res = _DuplicateHandle(int(source_process), int(source), int(target_process),
                           _ctypes.byref(target),
                           access, inherit, options)

    if not res:
        raise WindowsError("Error")

    return _handle(target.value)
DUPLICATE_SAME_ACCESS = 2


def CreateProcess(name, command_line, process_attr, thread_attr,
                  inherit, flags, env, start_dir, startup_info):
    _CreateProcess = _ctypes.WinDLL('kernel32').CreateProcessA
    _CreateProcess.argtypes = [_ctypes.c_char_p, _ctypes.c_char_p, _ctypes.c_void_p, _ctypes.c_void_p,
                               _ctypes.c_int, _ctypes.c_int, _ctypes.c_char_p, _ctypes.c_char_p,
                               _ctypes.c_void_p, _ctypes.c_void_p]
    _CreateProcess.restype = _ctypes.c_int

    class STARTUPINFO(_ctypes.Structure):
        _fields_ = [('cb',         _ctypes.c_int),
                    ('lpReserved', _ctypes.c_void_p),
                    ('lpDesktop',  _ctypes.c_char_p),
                    ('lpTitle',    _ctypes.c_char_p),
                    ('dwX',        _ctypes.c_int),
                    ('dwY',        _ctypes.c_int),
                    ('dwXSize',    _ctypes.c_int),
                    ('dwYSize',    _ctypes.c_int),
                    ('dwXCountChars', _ctypes.c_int),
                    ('dwYCountChars', _ctypes.c_int),
                    ("dwFillAttribute", _ctypes.c_int),
                    ("dwFlags", _ctypes.c_int),
                    ("wShowWindow", _ctypes.c_short),
                    ("cbReserved2", _ctypes.c_short),
                    ("lpReserved2", _ctypes.c_void_p),
                    ("hStdInput", _ctypes.c_int),
                    ("hStdOutput", _ctypes.c_int),
                    ("hStdError", _ctypes.c_int)
                    ]

    class PROCESS_INFORMATION(_ctypes.Structure):
        _fields_ = [("hProcess", _ctypes.c_int),
                    ("hThread", _ctypes.c_int),
                    ("dwProcessID", _ctypes.c_int),
                    ("dwThreadID", _ctypes.c_int)]
                
    si = STARTUPINFO()
    si.dwFlags = startup_info.dwFlags
    si.wShowWindow = getattr(startup_info, 'wShowWindow', 0)
    if startup_info.hStdInput:
        si.hStdInput = startup_info.hStdInput.handle
    if startup_info.hStdOutput:
        si.hStdOutput = startup_info.hStdOutput.handle
    if startup_info.hStdError:
        si.hStdError = startup_info.hStdError.handle

    pi = PROCESS_INFORMATION()

    if env is not None:
        envbuf = ""
        for k, v in env.iteritems():
            envbuf += "%s=%s\0" % (k, v)
        envbuf += '\0'
    else:
        envbuf = None

    res = _CreateProcess(name, command_line, None, None, inherit, flags, envbuf,
                        start_dir, _ctypes.byref(si), _ctypes.byref(pi))

    if not res:
        raise WindowsError("Error")

    return _handle(pi.hProcess), _handle(pi.hThread), pi.dwProcessID, pi.dwThreadID
STARTF_USESTDHANDLES = 0x100

def WaitForSingleObject(handle, milliseconds):
    _WaitForSingleObject = _ctypes.WinDLL('kernel32').WaitForSingleObject
    _WaitForSingleObject.argtypes = [_ctypes.c_int, _ctypes.c_int]
    _WaitForSingleObject.restype = _ctypes.c_int

    res = _WaitForSingleObject(handle.handle, milliseconds)

    if res < 0:
        raise WindowsError("Error")

    return res
INFINITE = 0xffffffff
WAIT_OBJECT_0 = 0

def GetExitCodeProcess(handle):
    _GetExitCodeProcess = _ctypes.WinDLL('kernel32').GetExitCodeProcess
    _GetExitCodeProcess.argtypes = [_ctypes.c_int, _ctypes.POINTER(_ctypes.c_int)]
    _GetExitCodeProcess.restype = _ctypes.c_int

    code = _ctypes.c_int()
    
    res = _GetExitCodeProcess(handle.handle, _ctypes.byref(code))

    if not res:
        raise WindowsError("Error")

    return code.value

def GetStdHandle(stdhandle):
    _GetStdHandle = _ctypes.WinDLL('kernel32').GetStdHandle
    _GetStdHandle.argtypes = [_ctypes.c_int]
    _GetStdHandle.restype = _ctypes.c_int

    res = _GetStdHandle(stdhandle)

    if not res:
        return None
    else:
        return res
STD_INPUT_HANDLE  = -10
STD_OUTPUT_HANDLE = -11
STD_ERROR_HANDLE  = -12
