/************************************************************/
/***  C header subsection: timestamp counter access       ***/


#if defined(USE_TSC)

typedef unsigned long long uint64;

/* prototypes */

uint64 LL_tsc_read(void);
long LL_tsc_read_diff(void);
void LL_tsc_reset_diff(void);

/* implementations */

#ifndef PYPY_NOT_MAIN_FILE

#if defined(__alpha__)

#define rdtscll(pcc) asm volatile ("rpcc %0" : "=r" (pcc))

#elif defined(__ppc__)

#define rdtscll(var) ppc_getcounter(&var)

static void
ppc_getcounter(uint64 *v)
{
	register unsigned long tbu, tb, tbu2;

  loop:
	asm volatile ("mftbu %0" : "=r" (tbu) );
	asm volatile ("mftb  %0" : "=r" (tb)  );
	asm volatile ("mftbu %0" : "=r" (tbu2));
	if (__builtin_expect(tbu != tbu2, 0)) goto loop;

	((long*)(v))[0] = tbu;
	((long*)(v))[1] = tb;
}

#else /* this section is for linux/x86 */

#define rdtscll(val) asm volatile ("rdtsc" : "=A" (val))

#endif

uint64
LL_tsc_read(void)
{
	uint64 tsc;
	rdtscll(tsc);

	return tsc;
}

static uint64 tsc_last = 0;

/* don't use for too long a diff, overflow problems:
   http://www.sandpile.org/post/msgs/20003444.htm */

long
LL_tsc_read_diff(void)
{
	uint64 new_tsc;
	unsigned long tsc_diff;

	/* returns garbage the first time you call it */
	rdtscll(new_tsc);
	tsc_diff = new_tsc - tsc_last;
	tsc_last = new_tsc;
	
	return tsc_diff;
}

void
LL_tsc_reset_diff(void)
{
	rdtscll(tsc_last);
}

#endif /* PYPY_NOT_MAIN_FILE */

#endif /* defined(USE_TSC) */

