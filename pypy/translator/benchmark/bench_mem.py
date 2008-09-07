#!/usr/bin/env python
""" Usage: bench_mem.py [-l log] program_name [arg0] [arg1] ...
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
        signal.signal(signal.SIGCHLD, lambda a,b: self.close())
        self.pid = run_child(name, args)
        self.results = []

    def loop(self, logfile, interval):
        if isinstance(logfile, basestring):
            logfile = open(logfile, 'w')
        counter = 0
        try:
            while 1:
                try:
                    res = parse_smaps_output(open('/proc/%d/smaps' % self.pid).read())
                    self.results.append((counter, res.private))
                    if logfile:
                        print >>logfile, counter, ' ', res.private
                except IOError:
                    return
                counter += 1
                time.sleep(interval)
        except (KeyboardInterrupt, SystemExit):
            os.kill(self.pid, signal.SIGTERM)
            raise

    def close(self):
        if self.pid != -1:
            self.realos.waitpid(self.pid, 0)
            self.pid = -1

    def __del__(self):
        self.close()

def run_child(name, args):
    pid = os.fork()
    if not pid:
        os.execvp(name, [name] + args)
    return pid

def parse_options(argv):
    num = 0
    logname = None
    while num < len(argv):
        arg = argv[num]
        if arg == '-l':
            logname = argv[num + 1]
            num += 1
        else:
            name = argv[num]
            if logname is None:
                logname = py.path.local(name).basename + '.log'
            args = argv[num + 1:]
            return logname, name, args
        num += 1
    raise Exception("Wrong arguments: %s" % (argv,))

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print __doc__
        sys.exit(1)
    logname, name, args = parse_options(sys.argv[1:])
    cp = ChildProcess(name, args)
    cp.loop(logname, 0)
