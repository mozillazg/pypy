// The Great Computer Language Shootout
// http://shootout.alioth.debian.org/
//
// contributed by Isaac Gouy 

var n = 10000000;
var partialSum = 0.0;
for (var d = 1; d <= n; d++) partialSum += 1.0/d;
print(partialSum);

