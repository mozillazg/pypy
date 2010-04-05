typedef struct {
    PyObject_HEAD
    void (*destructor)(void *);
} PyCObject;

