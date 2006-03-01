/************************************************************/
/***  C header subsection: transactional memory support   ***/

/* prototypes */
void LL_trans_begin(void);
void LL_trans_end(void);
void LL_trans_abort(void);
void LL_trans_pause(void);
void LL_trans_unpause(void);
void LL_trans_verbose(void);
void LL_trans_enable(void);
void LL_trans_disable(void);

/* implementations */

#ifndef PYPY_NOT_MAIN_FILE

#include <trans/primitives.h>

void
LL_trans_begin(void)
{
	XACT_BEGIN;
}

void
LL_trans_end(void)
{
	XACT_END;
}

void
LL_trans_abort(void)
{
	XACT_ABORT(&&abort);
	XACT_END;

 abort:
	;
}

/* XXX deliberately not RPyThreadTLS here => dependency problems */
static pthread_key_t pause_state_key = 0;

void
LL_trans_pause(void)
{
	int *pause_state;
	if (pause_state_key == 0)
		assert(pthread_key_create(&pause_state_key, free) == 0);
	pause_state = (int *)pthread_getspecific(pause_state_key);
	if (pause_state == NULL) {
		pause_state = malloc(sizeof(int));
		assert(pthread_setspecific(pause_state_key, pause_state) == 0);
	}
	XACT_PAUSE(*pause_state);
}

void
LL_trans_unpause(void)
{
	int *pause_state = (int *)pthread_getspecific(pause_state_key);
	assert(pause_state != NULL);
	XACT_UNPAUSE(*pause_state);
}

void
LL_trans_verbose(void)
{
	MY_MAGIC1(trans_verbose);
}

#include <sys/types.h>
#include <unistd.h>
#include <signal.h>

void
LL_trans_enable(void)
{
	int ret_val;
	ret_val = enable_transactions();
	assert(ret_val == 0);
	// XXX HACK HACK HACK, 1024 is first thread id
	if (pthread_self() == 1024) {
		static int suspended = 0;
		if (suspended)
			return;
		suspended = 1;
		pid_t pid = getpid();
		fprintf(stderr, "LL_trans_enable: suspending, pid is %d\n", pid);
		kill(pid, SIGSTOP);
	}
	XACT_BEGIN;
	XACT_PAUSE(ret_val);
	set_auto_xact(1);
	XACT_UNPAUSE(ret_val);
	XACT_END;
}

void
LL_trans_disable(void)
{
	set_auto_xact(0);
}

int
LL_trans_is_active(void)
{
	int ret_val;

	XACT_ACTIVE(ret_val);
	assert(ret_val == 0 || ret_val == 1);

	return ret_val;
}

#endif /* PYPY_NOT_MAIN_FILE */
