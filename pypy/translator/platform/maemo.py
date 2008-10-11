import py
from pypy.translator.platform.linux import Linux, _run_subprocess
from pypy.translator.platform import ExecutionResult, log

def check_scratchbox():
    if not py.path.local('/scratchbox/login').check():
        py.test.skip("No scratchbox detected")

class Maemo(Linux):
    def _execute_c_compiler(self, cc, args, outname):
        log.execute('/scratchbox/login ' + cc + ' ' + ' '.join(args))
        args = [cc] + args
        returncode, stdout, stderr = _run_subprocess('/scratchbox/login', args)
        self._handle_error(returncode, stderr, stdout, outname)
    
    def execute(self, executable, args=[], env=None):
        args = [str(executable)] + args
        log.message('executing /scratchbox/login ' + ' '.join(args))
        returncode, stdout, stderr = _run_subprocess('/scratchbox/login', args,
                                                     env)
        return ExecutionResult(returncode, stdout, stderr)

