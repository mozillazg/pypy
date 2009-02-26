nil addAst := nil
nil addTail := nil
Message addAst := method(
    "Ast(" print
    next addAst
)
Message pythonize := method(
    addAst
    "implicit" print
    addTail
)
Message addTail := method(
    ", \"" print
    name print
    "\"" print
    ", [" print 
    arguments foreach(i, argument, argument pythonize; ", " print)
    "])" print
    next addTail
)

in := File standardInput
lines := in readLines
in close
all := "" asMutable
lines foreach(i, line, all appendSeq(line, "\n"))

ms := Compiler messageForString(all) 
ms pythonize