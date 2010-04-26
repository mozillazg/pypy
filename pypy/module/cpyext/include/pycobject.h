#ifndef Py_COBJECT_H
#define Py_COBJECT_H
#ifdef __cplusplus
extern "C" {
#endif

#if (PY_VERSION_HEX >= 0x02060000 || defined(Py_BUILD_CORE))
typedef struct {
    PyObject_HEAD
    void *cobject;
    void *desc;
    void (*destructor)(void *);
} PyCObject;
#endif
 
#ifdef __cplusplus
}
#endif
#endif /* !Py_COBJECT_H */
