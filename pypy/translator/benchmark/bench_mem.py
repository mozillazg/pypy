#!/usr/bin/env python
import os
import py
import time
import re

class Result(object):
    def __init__(self, priv_map, shared_map, starttime=None):
        if starttime is None:
            starttime = time.time()
        self._compute_total(priv_map, shared_map)
        self.priv_map   = priv_map
        self.shared_map = shared_map

    def _compute_total(self, priv_map, shared_map):
        self.private = sum(priv_map.values())
        self.shared = sum(shared_map.values())
        
def parse_pmap_output(raw_data):
    def number(line):
        m = re.search('(\d+) kB', line)
        if not m:
            raise ValueError("Wrong line: %s" % (line,))
        return int(m.group(1))
    
    lines = raw_data.split('\n')[1:-1]
    priv_map = {}
    shared_map = {}
    num = 0
    while num < len(lines):
        m = re.search('(\S+)\s*$', lines[num])
        if not m:
            raise ValueError("Wrong line " + lines[num])
        name = m.group(1)
        priv = number(lines[num + 5]) + number(lines[num + 6])
        shared = number(lines[num + 3]) + number(lines[num + 4])
        if priv:
            assert not shared
            priv_map[name]   = priv + priv_map.get(name, 0)
        else:
            assert shared
            shared_map[name] = shared + shared_map.get(name, 0)
        num += 8
    return Result(priv_map, shared_map)

def run_child(name, args):
    pid = os.fork()
    if not pid:
        os.execvp(name, [name] + args)
    else:
        res = py.process.cmdexec('pmap -x %d' % pid)
    return res

if __name__ == '__main__':
    run_child('python', ['-c', 'pass'])
