#include <stdlib.h>


struct myjmpbuf {
  struct myjmpbuf *prev;
  void *esp;
  void *ebp;
  void *resumeaddr;
};

struct myjmpbuf *jmp_head;


void go_back(char *excdata) __attribute__ ((noreturn));
void go_back(char *excdata)
{
  asm volatile("movl	%0, %%esp\n\
	movl	%1, %%ebp\n\
	jmp	*%2" : :
               "g"(jmp_head->esp),
               "g"(jmp_head->ebp),
               "g"(jmp_head->resumeaddr),
               "b"(excdata));
  abort();
}

int h(int z)
{
  if (z > 0)
    go_back("some text");
  return 42;
}

int(*hptr)(int) = h;


int g(int x, int y)
{
  int z = x + y, u = x * y;
  struct myjmpbuf buf;
  char *excdata;
  buf.prev = jmp_head;
  jmp_head = &buf;
  asm volatile("xorl	%%ebx, %%ebx\n\
	movl	%%esp, %1\n\
	movl	%%ebp, %2\n\
	movl	$0f, %3\n\
0:" :
               "=b"(excdata) :
               "m"(buf.esp), "m"(buf.ebp), "m"(buf.resumeaddr) :
               "eax", "edx", "ecx", "esi", "edi", "memory", "cc");
  if (excdata != NULL)
    {
      printf("back to the setjmp point with excdata=%s\n",
             excdata);
    }
  else
    {
      printf("direct run\n");
      hptr(z+u);
      printf("done\n");
    }
  printf("x=%d, y=%d, z=%d, u=%d\n", x, y, z, u);
}

int main()
{
  g(4, 7);
}
