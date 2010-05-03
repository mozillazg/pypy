
import os

x = [chr(i) for i in range(256)]

class ChunkedList(object):
    def __init__(self, chunk_size=256):
        self.l = []
        self.count = 0
        self.chunk_size = chunk_size

    def append(self, element):
        if self.count % self.chunk_size == 0:
            # end of chunk
            self.l.append([None] * self.chunk_size)
        self.l[-1][self.count % self.chunk_size] = element
        self.count += 1

def main(no, chunk_size):
    l = ChunkedList(chunk_size)
    for i in range(no):
        l.append("abc" + x[i % 256])
    return 3

def entry_point(argv):
    if len(argv) != 3:
        print "Provide 2 ints as args"
        return 1
    main(int(argv[1]), int(argv[2]))
    return 0

def target(*args):
    return entry_point, None
