
// some simple number-crunching benchmarks

function f1(n) {
  var i = 0;
  var x = 1;
  while (i < n) {
    var j = 0;
    while (j <= i) {
      j++;
      x = x + (i&j);
    }
    i++;
  }
  return x;
}

a = new Date();
f1(2117);
b = new Date();
print(b - a);

