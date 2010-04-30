#include "Python.h"

static PyMethodDef date_functions[] = {
    {NULL, NULL}
};

void initdate(void)
{
    Py_InitModule("date", date_functions);
    PyImport_ImportModule("apple.banana");
}
