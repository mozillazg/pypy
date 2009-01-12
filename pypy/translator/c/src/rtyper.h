/************************************************************/
 /***  C header subsection: tools for RTyper-aware code    ***/

#include <string.h>


#define RPyString_Size(rps)		((rps)->rs_chars.length)


/* prototypes */

char *RPyString_AsCharP(RPyString *rps);
void RPyString_FreeCache(void);
RPyString *RPyString_FromString(char *buf);


/* implementations */

#ifndef PYPY_NOT_MAIN_FILE

struct _RPyString_dump_t {
	struct _RPyString_dump_t *next;
	char data[1];
} *_RPyString_dump = NULL;

char *RPyString_AsCharP(RPyString *rps)
{
	long len = RPyString_Size(rps);
	struct _RPyString_dump_t *dump = \
			malloc(sizeof(struct _RPyString_dump_t) + len);
	if (!dump)
		return "(out of memory!)";
	dump->next = _RPyString_dump;
	_RPyString_dump = dump;
	memcpy(dump->data, rps->rs_chars.items, len);
	dump->data[len] = 0;
	return dump->data;
}

void RPyString_FreeCache(void)
{
	while (_RPyString_dump) {
		struct _RPyString_dump_t *dump = _RPyString_dump;
		_RPyString_dump = dump->next;
		free(dump);
	}
}

RPyString *RPyString_FromString(char *buf)
{
	int length = strlen(buf);
	RPyString *rps = RPyString_New(length);
	memcpy(rps->rs_chars.items, buf, length);
	return rps;
}

#endif /* PYPY_NOT_MAIN_FILE */
