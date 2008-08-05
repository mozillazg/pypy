from sup import run

def w(N, start):
    d = {}
    d1 = {}
    start()
    i = 0
    u = dict.update
    while i < N:
        u(d, d1)
        u(d, d1)
        u(d, d1)
        i+=1
    
run(w, 1000)
