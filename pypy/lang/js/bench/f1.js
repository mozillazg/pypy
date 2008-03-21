
// some simple number-crunching benchmark

function f1(n) {
  var i = 0;
  var x = 1;
  while (i < n) {
    var j = 0;
    while (j <= i) {
      j = j + 1;
      x = x + (i&j);
    }
    i = i + 1;
  }
  return x;
}

//a = new Date();
print(f1(2117));
//b = new Date();
//print(b - a);

