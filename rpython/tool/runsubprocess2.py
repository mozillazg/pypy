
import os, sys, time, select
from subprocess import Popen, PIPE
import twisted

_child = None
_source = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_source = os.path.join(os.path.join(_source, 'translator'), 'invoker.py')

def spawn_subprocess():
    global _child
    _child = Popen([sys.executable, '-u', _source], bufsize=0,
                   stdin=PIPE, stdout=PIPE, stderr=PIPE, close_fds=True)
spawn_subprocess()

def cleanup_subprocess():
    global _child
    _child = None
import atexit; atexit.register(cleanup_subprocess)

def run(exe, *args):
    _child.stdin.write(repr((exe,) + args) + "\n")

class SubprocessExploded(Exception):
    pass

def results():
    results = []
    while True:
        rl, _, _ = select.select([_child.stdout, _child.stderr], [], [], 0)
        if _child.stderr in rl:
            raise SubprocessExploded(_child.stderr)
        elif _child.stdout in rl:
            results.append(eval(_child.stdout.readline()))
        else:
            return results
