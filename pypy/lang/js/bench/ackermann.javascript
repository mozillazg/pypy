// The Great Computer Language Shootout
// http://shootout.alioth.debian.org/
//
// contributed by Sjoerd Visscher

function ack(m, n) {
  return (m == 0
    ? n + 1
    : (n == 0
      ? ack(m - 1, 1) 
      : ack(m - 1, ack(m, n - 1))));
}

var n = arguments[0];
print("ack(3, " + n + "): " + ack(3, n));
