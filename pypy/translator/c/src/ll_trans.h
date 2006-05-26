/************************************************************/
/***  C header subsection: transactional memory support   ***/

/* prototypes */
void LL_trans_begin(void);
void LL_trans_end(void);
void LL_trans_retry(void);
void LL_trans_abort(void);
void LL_trans_pause(void);
void LL_trans_unpause(void);
void LL_trans_verbose(void);
void LL_trans_enable(void);
void LL_trans_disable(void);
int RPyTransPause(void);
void RPyTransUnpause(int pause_state);
void RPyTransSurroundSyscalls(int surround);

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
LL_trans_retry(void)
{
	XACT_RETRY;
}

void
LL_trans_abort(void)
{
	XACT_ABORT(&&abort);
	XACT_END;

 abort:
	;
}

int
RPyTransPause(void)
{
	int pause_state;
	XACT_PAUSE(pause_state);
	return pause_state;
}

void
RPyTransUnpause(int pause_state)
{
	XACT_UNPAUSE(pause_state);
}

void
RPyTransSurroundSyscalls(int surround)
{
	if (surround) {
		int pause_state;
		XACT_PAUSE(pause_state);
		set_auto_xact(1);
		XACT_UNPAUSE(pause_state);
	} else {
		set_auto_xact(0);
	}
}

static __thread int pause_state;

void
LL_trans_pause(void)
{
	XACT_PAUSE(pause_state);
}

void
LL_trans_unpause(void)
{
	XACT_UNPAUSE(pause_state);
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
	if (ret_val != 0) {
		pid_t pid = getpid();
		char *map_path;
		asprintf(&map_path, "/proc/%d/maps", pid);
		if ( (pid = fork()) == 0) {
			execlp("cat", "cat", map_path, NULL);
			exit(0);
		}
		free(map_path);
		waitpid(pid, NULL, 0);
		printf("Load transactional memory module and press return\n");
		while (getchar() != '\n');
		ret_val = enable_transactions();
		assert(ret_val == 0);
	}
	XACT_BEGIN;
	RPyTransSurroundSyscalls(1);
	XACT_END;
}

void
LL_trans_disable(void)
{
	RPyTransSurroundSyscalls(0);
}

int
LL_trans_is_active(void)
{
	int ret_val;

	XACT_ACTIVE(ret_val);
	if (ret_val != 0 && ret_val != 1)
		return 0;

	return ret_val;
}

void
LL_trans_reset_stats(void)
{
	XACT_DUMP_STATS(2);
}

#endif /* PYPY_NOT_MAIN_FILE */
