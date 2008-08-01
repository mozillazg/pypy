import sys, time

def ref(N, start):
    start()
    i = 0
    while i < N:
        i+=1


def run(func, n):
    n *= int(sys.argv[1])
    st = [None]
    t = time.time

    def start():
        st[0] = t()

    ref(n, start)
    elapsed_ref = t() - st[0]

    func(n, start)
    elapsed = t() - st[0]

    #if elapsed < elapsed_ref*10:
    #    print "not enough meat", elapsed, elapsed_ref

    print sys.argv[0].replace('.py', ''), elapsed-elapsed_ref
    

