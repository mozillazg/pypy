
from pypy.rlib.streamio import fdopen_as_stream

def target(*args):
    return main, None

def main(args):
    search = args[0]
    FD = 0
    s = fdopen_as_stream(FD, 'r', 1024)
    while True:
        next_line = s.readline()
        if not next_line:
            break
        if search in next_line:
            print next_line
    return 0

def cpy_main(s):
    for x in sys.stdin.readlines():
        if s in x:
            print x

if __name__ == '__main__':
    import sys
    cpy_main(sys.argv[1])
