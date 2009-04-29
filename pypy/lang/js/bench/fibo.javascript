// The Great Computer Language Shootout
// http://shootout.alioth.debian.org/
//
// contributed by David Hedbor
// modified by Isaac Gouy

function fib(n) {
    if (n < 2) return 1;
    return fib(n-2) + fib(n-1);
}

var n = arguments[0];
print(fib(n));

