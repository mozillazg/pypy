#!/usr/bin/env python
""" Usage: bench_mem.py program_name [arg0] [arg1] ...
"""
import os
import py
import time
import re
import signal
import sys

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
        
def parse_smaps_output(raw_data):
    def number(line):
        m = re.search('(\d+) kB', line)
        if not m:
            raise ValueError("Wrong line: %s" % (line,))
        return int(m.group(1))
    
    lines = [i for i in raw_data.split('\n')[:-1] if i]
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
            priv_map[name]   = priv + priv_map.get(name, 0)
        if shared:
            shared_map[name] = shared + shared_map.get(name, 0)
        num += 8
    return Result(priv_map, shared_map)

class ChildProcess(object):
    realos = os
    
    def __init__(self, name, args):
        self.pid = run_child(name, args)

    def loop(self, logfile, interval):
        if isinstance(logfile, basestring):
            logfile = open(logfile, 'w')
        counter = 0
        while 1:
            try:
                res = parse_smaps_output(open('/proc/%d/smaps' % self.pid).read())
                print >>logfile, counter, ' ', res.private
            except IOError:
                self.close()
                return
            counter += 1
            time.sleep(interval)

    def close(self):
        if self.pid:
            self.realos.waitpid(self.pid, 0)

    def __del__(self):
        self.close()

def run_child(name, args):
    pid = os.fork()
    if not pid:
        os.execvp(name, [name] + args)
    return pid

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print __doc__
        sys.exit(1)
    cp = ChildProcess(sys.argv[1], sys.argv[2:])
    cp.loop(sys.stdout, 0.1)
