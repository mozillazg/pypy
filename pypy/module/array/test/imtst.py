def f():
    a=(1,2,3)
    s=0
    while s<1000:
        s+=a[0]
        
def g():
    s=0
    while s<1000:
        s+=1
    return s
        

def h():
    s=0
    i=0
    a=7
    while i<100000:
        s+=i
        i+=1
    return s

def h2():
    s=0
    i=0
    a=(1,7,42)
    while i<100000:
        s+=a[1]
        i+=1
    return s

def ff():
    s=0
    i=0
    while i<100000:
        s+=i
        i+=1
        if i>50000:
            i=float(i)

print ff()
