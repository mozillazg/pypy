nil addArguments := nil
nil pythonize := nil

Message pythonize := method(
    "(" print
    addArguments
    next pythonize
    ")" print 
    
)
Message addArguments := method(
    "\"" print
    name asMutable escape print
    "\"" print
    "[" print 
    arguments foreach(i, argument, argument pythonize; "," print)
    "]" print
)

in := File standardInput
lines := in readLines
in close
all := "" asMutable
lines foreach(i, line, all appendSeq(line, "\n"))

ms := Compiler messageForString(all) 
ms pythonize