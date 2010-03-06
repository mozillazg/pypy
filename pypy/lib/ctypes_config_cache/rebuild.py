#! /usr/bin/env python
# Run this script to rebuild all caches from the *.ctc.py files.

import autopath
import os, sys

_dirpath = os.path.dirname(__file__)


def rebuild_one(name):
    filename = os.path.join(_dirpath, name)
    d = {'__file__': filename}
    path = sys.path[:]
    try:
        sys.path.insert(0, _dirpath)
        execfile(filename, d)
    finally:
        sys.path[:] = path

def rebuild():
    for p in os.listdir(_dirpath):
        if p.endswith('.ctc.py'):
            rebuild_one(p)


if __name__ == '__main__':
    rebuild()
