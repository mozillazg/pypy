#ifndef Py_STRUCTMEMBER_H
#define Py_STRUCTMEMBER_H
#ifdef __cplusplus
extern "C" {
#endif


#ifndef offsetof
#define offsetof(type, member) ( (int) & ((type*)0) -> member )
#endif


typedef struct PyMemberDef {
	/* Current version, use this */
	char *name;
	int type;
	Py_ssize_t offset;
	int flags;
	char *doc;
} PyMemberDef;


/* Types */
#define T_INT		1

/* Flags */
#define READONLY      1
#define RO            READONLY                /* Shorthand */


#ifdef __cplusplus
}
#endif
#endif /* !Py_STRUCTMEMBER_H */
