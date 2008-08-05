from sup import run

def w(N, start):
    d = {}
    d1 = {}
    start()
    i = 0
    while i < N:
        d.update(d1)
        d.update(d1)
        d.update(d1)
        i+=1
    
run(w, 1000)
