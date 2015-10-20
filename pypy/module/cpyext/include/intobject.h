
/* Int object interface */

#ifndef Py_INTOBJECT_H
#define Py_INTOBJECT_H
#ifdef __cplusplus
extern "C" {
#endif


typedef struct {
    PyObject_HEAD
    long ob_ival;
} PyIntObject;

/* Macro, trading safety for speed */
#define PyInt_AS_LONG(op) (((PyIntObject *)(op))->ob_ival)


#ifdef __cplusplus
}
#endif
#endif /* !Py_BOOLOBJECT_H */
