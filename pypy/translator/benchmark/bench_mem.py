#!/usr/bin/env python
import os
import py

def run_child(name, args):
    pid = os.fork()
    if not pid:
        os.execvp(name, [name] + args)
    else:
        res = py.process.cmdexec('pmap -d %d' % pid)
    return res

if __name__ == '__main__':
    run_child('python', ['-c', 'pass'])
