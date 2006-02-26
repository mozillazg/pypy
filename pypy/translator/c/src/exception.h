
/************************************************************/
 /***  C header subsection: exceptions                     ***/

#if !defined(PYPY_STANDALONE) && !defined(PYPY_NOT_MAIN_FILE)
   PyObject *RPythonError;
#endif 

/******************************************************************/
#ifdef HAVE_RTYPER               /* RPython version of exceptions */
/******************************************************************/

#ifdef PYPY_NOT_MAIN_FILE
#ifdef WITH_THREAD
extern RPyThreadTLS             rpython_exc_type_key;
extern RPyThreadTLS             rpython_exc_value_key;
#else
extern RPYTHON_EXCEPTION_VTABLE	rpython_exc_type;
extern RPYTHON_EXCEPTION	rpython_exc_value;
#endif /* WITH_THREAD */
#else
#ifdef WITH_THREAD
RPyThreadTLS            	rpython_exc_type_key = 0;
RPyThreadTLS            	rpython_exc_value_key = 0;
#else
RPYTHON_EXCEPTION_VTABLE	rpython_exc_type = NULL;
RPYTHON_EXCEPTION		rpython_exc_value = NULL;
#endif /* WITH_THREAD */
#endif /* PYPY_NOT_MAIN_FILE */

#ifdef WITH_THREAD
#define rpython_exc_type						\
	((RPYTHON_EXCEPTION_VTABLE)RPyThreadTLS_Get(rpython_exc_type_key))
#define rpython_exc_value						\
	((RPYTHON_EXCEPTION)RPyThreadTLS_Get(rpython_exc_value_key))
#define _RPySetException(etype, evalue)                                 \
		RPyThreadTLS_Set(rpython_exc_type_key, etype);       \
		RPyThreadTLS_Set(rpython_exc_value_key, evalue);
#else
#define _RPySetException(etype, evalue)			\
		rpython_exc_type = etype;		\
		rpython_exc_value = evalue
#endif /* WITH_THREAD */

#define RPyExceptionOccurred()	(rpython_exc_type != NULL)

#define RPyRaiseException(etype, evalue)	do {	\
		assert(!RPyExceptionOccurred());	\
		_RPySetException(etype, evalue);	\
	} while (0)

#define RPyFetchException(etypevar, evaluevar, type_of_evaluevar) do {  \
		etypevar = rpython_exc_type;				\
		evaluevar = (type_of_evaluevar) rpython_exc_value;	\
		_RPySetException(NULL, NULL);				\
	} while (0)

#define RPyMatchException(etype)	RPYTHON_EXCEPTION_MATCH(rpython_exc_type,  \
					(RPYTHON_EXCEPTION_VTABLE) etype)


/* prototypes */

#define RPyRaiseSimpleException(exc, msg)   _RPyRaiseSimpleException(R##exc)
void _RPyRaiseSimpleException(RPYTHON_EXCEPTION rexc);

#ifndef PYPY_STANDALONE
void RPyConvertExceptionFromCPython(void);
void _RPyConvertExceptionToCPython(void);
#define RPyConvertExceptionToCPython(vanishing)    \
	_RPyConvertExceptionToCPython();		\
	vanishing = rpython_exc_value;		\
	rpython_exc_type = NULL;		\
	rpython_exc_value = NULL
#endif


/* implementations */

#ifndef PYPY_NOT_MAIN_FILE

void _RPyRaiseSimpleException(RPYTHON_EXCEPTION rexc)
{
	/* XXX 1. uses officially bad fishing */
	/* XXX 2. msg is ignored */
	_RPySetException(rexc->o_typeptr, rexc);
	PUSH_ALIVE(rpython_exc_value);
}

#ifndef PYPY_STANDALONE
void RPyConvertExceptionFromCPython(void)
{
	/* convert the CPython exception to an RPython one */
	PyObject *exc_type, *exc_value, *exc_tb;
	assert(PyErr_Occurred());
	assert(!RPyExceptionOccurred());
	PyErr_Fetch(&exc_type, &exc_value, &exc_tb);
	/* XXX losing the error message here */
	rpython_exc_value = RPYTHON_PYEXCCLASS2EXC(exc_type);
	rpython_exc_type = RPYTHON_TYPE_OF_EXC_INST(rpython_exc_value);
}

void _RPyConvertExceptionToCPython(void)
{
	/* XXX 1. uses officially bad fishing */
	/* XXX 2. looks for exception classes by name, fragile */
	char* clsname;
	PyObject* pycls;
	assert(RPyExceptionOccurred());
	assert(!PyErr_Occurred());
	clsname = rpython_exc_type->ov_name->items;
	pycls = PyDict_GetItemString(PyEval_GetBuiltins(), clsname);
	if (pycls != NULL && PyClass_Check(pycls) &&
	    PyClass_IsSubclass(pycls, PyExc_Exception)) {
		PyErr_SetNone(pycls);
	}
	else {
		PyErr_SetString(RPythonError, clsname);
	}
}
#endif   /* !PYPY_STANDALONE */

#endif /* PYPY_NOT_MAIN_FILE */



/******************************************************************/
#else    /* non-RPython version of exceptions, using CPython only */
/******************************************************************/

#define RPyExceptionOccurred()           PyErr_Occurred()
#define RPyRaiseException(etype, evalue) PyErr_Restore(etype, evalue, NULL)
#define RPyFetchException(etypevar, evaluevar, ignored)  do {	\
		PyObject *__tb;					\
		PyErr_Fetch(&etypevar, &evaluevar, &__tb);	\
		if (evaluevar == NULL) {			\
			evaluevar = Py_None;			\
			Py_INCREF(Py_None);			\
		}						\
		Py_XDECREF(__tb);				\
	} while (0)
#define RPyMatchException(etype)         PyErr_ExceptionMatches(etype)
#define RPyConvertExceptionFromCPython() /* nothing */
#define RPyConvertExceptionToCPython(vanishing) vanishing = NULL  

#define RPyRaiseSimpleException(exc, msg) \
		PyErr_SetString(exc, msg)

/******************************************************************/
#endif                                             /* HAVE_RTYPER */
/******************************************************************/
