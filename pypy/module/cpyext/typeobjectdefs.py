from pypy.module.cpyext.api import h


freefunc = h.definitions['freefunc'].OF
destructor = h.definitions['destructor'].OF
printfunc = h.definitions['printfunc'].OF
getattrfunc = h.definitions['getattrfunc'].OF
getattrofunc = h.definitions['getattrofunc'].OF
setattrfunc = h.definitions['setattrfunc'].OF
setattrofunc = h.definitions['setattrofunc'].OF
cmpfunc = h.definitions['cmpfunc'].OF
reprfunc = h.definitions['reprfunc'].OF
hashfunc = h.definitions['hashfunc'].OF
richcmpfunc = h.definitions['richcmpfunc'].OF
getiterfunc = h.definitions['getiterfunc'].OF
iternextfunc = h.definitions['iternextfunc'].OF
descrgetfunc = h.definitions['descrgetfunc'].OF
descrsetfunc = h.definitions['descrsetfunc'].OF
initproc = h.definitions['initproc'].OF
newfunc = h.definitions['newfunc'].OF
allocfunc = h.definitions['allocfunc'].OF

unaryfunc = h.definitions['unaryfunc'].OF
binaryfunc = h.definitions['binaryfunc'].OF
ternaryfunc = h.definitions['ternaryfunc'].OF
inquiry = h.definitions['inquiry'].OF
lenfunc = h.definitions['lenfunc'].OF
coercion = h.definitions['coercion'].OF
intargfunc = h.definitions['intargfunc'].OF
intintargfunc = h.definitions['intintargfunc'].OF
ssizeargfunc = h.definitions['ssizeargfunc'].OF
ssizessizeargfunc = h.definitions['ssizessizeargfunc'].OF
intobjargproc = h.definitions['intobjargproc'].OF
intintobjargproc = h.definitions['intintobjargproc'].OF
ssizeobjargproc = h.definitions['ssizeobjargproc'].OF
ssizessizeobjargproc = h.definitions['ssizessizeobjargproc'].OF
objobjargproc = h.definitions['objobjargproc'].OF

objobjproc = h.definitions['objobjproc'].OF
visitproc = h.definitions['visitproc'].OF
traverseproc = h.definitions['traverseproc'].OF

getter = h.definitions['getter'].OF
setter = h.definitions['setter'].OF

#wrapperfunc = h.definitions['wrapperfunc']
#wrapperfunc_kwds = h.definitions['wrapperfunc_kwds']

readbufferproc = h.definitions['readbufferproc'].OF
writebufferproc = h.definitions['writebufferproc'].OF
segcountproc = h.definitions['segcountproc'].OF
charbufferproc = h.definitions['charbufferproc'].OF
getbufferproc = h.definitions['getbufferproc'].OF
releasebufferproc = h.definitions['releasebufferproc'].OF


PyGetSetDef = h.definitions['PyGetSetDef'].OF
PyNumberMethods = h.definitions['PyNumberMethods'].OF
PySequenceMethods = h.definitions['PySequenceMethods'].OF
PyMappingMethods = h.definitions['PyMappingMethods'].OF
PyBufferProcs = h.definitions['PyBufferProcs'].OF
PyMemberDef = h.definitions['PyMemberDef'].OF
