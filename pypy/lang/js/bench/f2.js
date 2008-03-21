
function fib(n) {
  if ((n == 0) || (n == 1))
     return(0);
  return fib(n-1)+fib(n-2);
}

fib(28);
