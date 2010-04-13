#ifndef Py_PYSTATE_H
#define Py_PYSTATE_H

typedef struct _ts {
    int initialized; // not used
} PyThreadState;

#define Py_BEGIN_ALLOW_THREADS { \
			PyThreadState *_save; \
			_save = PyEval_SaveThread();
#define Py_BLOCK_THREADS	PyEval_RestoreThread(_save);
#define Py_UNBLOCK_THREADS	_save = PyEval_SaveThread();
#define Py_END_ALLOW_THREADS	PyEval_RestoreThread(_save); \
		 }

#endif /* !Py_PYSTATE_H */
