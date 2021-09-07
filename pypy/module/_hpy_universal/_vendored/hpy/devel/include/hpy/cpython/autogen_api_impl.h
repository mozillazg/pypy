
/*
   DO NOT EDIT THIS FILE!

   This file is automatically generated by hpy.tools.autogen.trampolines.cpython_autogen_api_impl_h
   See also hpy.tools.autogen and hpy/tools/public_api.h

   Run this to regenerate:
       make autogen

*/

HPyAPI_FUNC HPy HPyLong_FromLong(HPyContext *ctx, long value)
{
    return _py2h(PyLong_FromLong(value));
}

HPyAPI_FUNC HPy HPyLong_FromUnsignedLong(HPyContext *ctx, unsigned long value)
{
    return _py2h(PyLong_FromUnsignedLong(value));
}

HPyAPI_FUNC HPy HPyLong_FromLongLong(HPyContext *ctx, long long v)
{
    return _py2h(PyLong_FromLongLong(v));
}

HPyAPI_FUNC HPy HPyLong_FromUnsignedLongLong(HPyContext *ctx, unsigned long long v)
{
    return _py2h(PyLong_FromUnsignedLongLong(v));
}

HPyAPI_FUNC HPy HPyLong_FromSize_t(HPyContext *ctx, size_t value)
{
    return _py2h(PyLong_FromSize_t(value));
}

HPyAPI_FUNC HPy HPyLong_FromSsize_t(HPyContext *ctx, HPy_ssize_t value)
{
    return _py2h(PyLong_FromSsize_t(value));
}

HPyAPI_FUNC long HPyLong_AsLong(HPyContext *ctx, HPy h)
{
    return PyLong_AsLong(_h2py(h));
}

HPyAPI_FUNC unsigned long HPyLong_AsUnsignedLong(HPyContext *ctx, HPy h)
{
    return PyLong_AsUnsignedLong(_h2py(h));
}

HPyAPI_FUNC unsigned long HPyLong_AsUnsignedLongMask(HPyContext *ctx, HPy h)
{
    return PyLong_AsUnsignedLongMask(_h2py(h));
}

HPyAPI_FUNC long long HPyLong_AsLongLong(HPyContext *ctx, HPy h)
{
    return PyLong_AsLongLong(_h2py(h));
}

HPyAPI_FUNC unsigned long long HPyLong_AsUnsignedLongLong(HPyContext *ctx, HPy h)
{
    return PyLong_AsUnsignedLongLong(_h2py(h));
}

HPyAPI_FUNC unsigned long long HPyLong_AsUnsignedLongLongMask(HPyContext *ctx, HPy h)
{
    return PyLong_AsUnsignedLongLongMask(_h2py(h));
}

HPyAPI_FUNC size_t HPyLong_AsSize_t(HPyContext *ctx, HPy h)
{
    return PyLong_AsSize_t(_h2py(h));
}

HPyAPI_FUNC HPy_ssize_t HPyLong_AsSsize_t(HPyContext *ctx, HPy h)
{
    return PyLong_AsSsize_t(_h2py(h));
}

HPyAPI_FUNC HPy HPyFloat_FromDouble(HPyContext *ctx, double v)
{
    return _py2h(PyFloat_FromDouble(v));
}

HPyAPI_FUNC double HPyFloat_AsDouble(HPyContext *ctx, HPy h)
{
    return PyFloat_AsDouble(_h2py(h));
}

HPyAPI_FUNC HPy HPyBool_FromLong(HPyContext *ctx, long v)
{
    return _py2h(PyBool_FromLong(v));
}

HPyAPI_FUNC HPy_ssize_t HPy_Length(HPyContext *ctx, HPy h)
{
    return PyObject_Length(_h2py(h));
}

HPyAPI_FUNC int HPyNumber_Check(HPyContext *ctx, HPy h)
{
    return PyNumber_Check(_h2py(h));
}

HPyAPI_FUNC HPy HPy_Add(HPyContext *ctx, HPy h1, HPy h2)
{
    return _py2h(PyNumber_Add(_h2py(h1), _h2py(h2)));
}

HPyAPI_FUNC HPy HPy_Subtract(HPyContext *ctx, HPy h1, HPy h2)
{
    return _py2h(PyNumber_Subtract(_h2py(h1), _h2py(h2)));
}

HPyAPI_FUNC HPy HPy_Multiply(HPyContext *ctx, HPy h1, HPy h2)
{
    return _py2h(PyNumber_Multiply(_h2py(h1), _h2py(h2)));
}

HPyAPI_FUNC HPy HPy_MatrixMultiply(HPyContext *ctx, HPy h1, HPy h2)
{
    return _py2h(PyNumber_MatrixMultiply(_h2py(h1), _h2py(h2)));
}

HPyAPI_FUNC HPy HPy_FloorDivide(HPyContext *ctx, HPy h1, HPy h2)
{
    return _py2h(PyNumber_FloorDivide(_h2py(h1), _h2py(h2)));
}

HPyAPI_FUNC HPy HPy_TrueDivide(HPyContext *ctx, HPy h1, HPy h2)
{
    return _py2h(PyNumber_TrueDivide(_h2py(h1), _h2py(h2)));
}

HPyAPI_FUNC HPy HPy_Remainder(HPyContext *ctx, HPy h1, HPy h2)
{
    return _py2h(PyNumber_Remainder(_h2py(h1), _h2py(h2)));
}

HPyAPI_FUNC HPy HPy_Divmod(HPyContext *ctx, HPy h1, HPy h2)
{
    return _py2h(PyNumber_Divmod(_h2py(h1), _h2py(h2)));
}

HPyAPI_FUNC HPy HPy_Power(HPyContext *ctx, HPy h1, HPy h2, HPy h3)
{
    return _py2h(PyNumber_Power(_h2py(h1), _h2py(h2), _h2py(h3)));
}

HPyAPI_FUNC HPy HPy_Negative(HPyContext *ctx, HPy h1)
{
    return _py2h(PyNumber_Negative(_h2py(h1)));
}

HPyAPI_FUNC HPy HPy_Positive(HPyContext *ctx, HPy h1)
{
    return _py2h(PyNumber_Positive(_h2py(h1)));
}

HPyAPI_FUNC HPy HPy_Absolute(HPyContext *ctx, HPy h1)
{
    return _py2h(PyNumber_Absolute(_h2py(h1)));
}

HPyAPI_FUNC HPy HPy_Invert(HPyContext *ctx, HPy h1)
{
    return _py2h(PyNumber_Invert(_h2py(h1)));
}

HPyAPI_FUNC HPy HPy_Lshift(HPyContext *ctx, HPy h1, HPy h2)
{
    return _py2h(PyNumber_Lshift(_h2py(h1), _h2py(h2)));
}

HPyAPI_FUNC HPy HPy_Rshift(HPyContext *ctx, HPy h1, HPy h2)
{
    return _py2h(PyNumber_Rshift(_h2py(h1), _h2py(h2)));
}

HPyAPI_FUNC HPy HPy_And(HPyContext *ctx, HPy h1, HPy h2)
{
    return _py2h(PyNumber_And(_h2py(h1), _h2py(h2)));
}

HPyAPI_FUNC HPy HPy_Xor(HPyContext *ctx, HPy h1, HPy h2)
{
    return _py2h(PyNumber_Xor(_h2py(h1), _h2py(h2)));
}

HPyAPI_FUNC HPy HPy_Or(HPyContext *ctx, HPy h1, HPy h2)
{
    return _py2h(PyNumber_Or(_h2py(h1), _h2py(h2)));
}

HPyAPI_FUNC HPy HPy_Index(HPyContext *ctx, HPy h1)
{
    return _py2h(PyNumber_Index(_h2py(h1)));
}

HPyAPI_FUNC HPy HPy_Long(HPyContext *ctx, HPy h1)
{
    return _py2h(PyNumber_Long(_h2py(h1)));
}

HPyAPI_FUNC HPy HPy_Float(HPyContext *ctx, HPy h1)
{
    return _py2h(PyNumber_Float(_h2py(h1)));
}

HPyAPI_FUNC HPy HPy_InPlaceAdd(HPyContext *ctx, HPy h1, HPy h2)
{
    return _py2h(PyNumber_InPlaceAdd(_h2py(h1), _h2py(h2)));
}

HPyAPI_FUNC HPy HPy_InPlaceSubtract(HPyContext *ctx, HPy h1, HPy h2)
{
    return _py2h(PyNumber_InPlaceSubtract(_h2py(h1), _h2py(h2)));
}

HPyAPI_FUNC HPy HPy_InPlaceMultiply(HPyContext *ctx, HPy h1, HPy h2)
{
    return _py2h(PyNumber_InPlaceMultiply(_h2py(h1), _h2py(h2)));
}

HPyAPI_FUNC HPy HPy_InPlaceMatrixMultiply(HPyContext *ctx, HPy h1, HPy h2)
{
    return _py2h(PyNumber_InPlaceMatrixMultiply(_h2py(h1), _h2py(h2)));
}

HPyAPI_FUNC HPy HPy_InPlaceFloorDivide(HPyContext *ctx, HPy h1, HPy h2)
{
    return _py2h(PyNumber_InPlaceFloorDivide(_h2py(h1), _h2py(h2)));
}

HPyAPI_FUNC HPy HPy_InPlaceTrueDivide(HPyContext *ctx, HPy h1, HPy h2)
{
    return _py2h(PyNumber_InPlaceTrueDivide(_h2py(h1), _h2py(h2)));
}

HPyAPI_FUNC HPy HPy_InPlaceRemainder(HPyContext *ctx, HPy h1, HPy h2)
{
    return _py2h(PyNumber_InPlaceRemainder(_h2py(h1), _h2py(h2)));
}

HPyAPI_FUNC HPy HPy_InPlacePower(HPyContext *ctx, HPy h1, HPy h2, HPy h3)
{
    return _py2h(PyNumber_InPlacePower(_h2py(h1), _h2py(h2), _h2py(h3)));
}

HPyAPI_FUNC HPy HPy_InPlaceLshift(HPyContext *ctx, HPy h1, HPy h2)
{
    return _py2h(PyNumber_InPlaceLshift(_h2py(h1), _h2py(h2)));
}

HPyAPI_FUNC HPy HPy_InPlaceRshift(HPyContext *ctx, HPy h1, HPy h2)
{
    return _py2h(PyNumber_InPlaceRshift(_h2py(h1), _h2py(h2)));
}

HPyAPI_FUNC HPy HPy_InPlaceAnd(HPyContext *ctx, HPy h1, HPy h2)
{
    return _py2h(PyNumber_InPlaceAnd(_h2py(h1), _h2py(h2)));
}

HPyAPI_FUNC HPy HPy_InPlaceXor(HPyContext *ctx, HPy h1, HPy h2)
{
    return _py2h(PyNumber_InPlaceXor(_h2py(h1), _h2py(h2)));
}

HPyAPI_FUNC HPy HPy_InPlaceOr(HPyContext *ctx, HPy h1, HPy h2)
{
    return _py2h(PyNumber_InPlaceOr(_h2py(h1), _h2py(h2)));
}

HPyAPI_FUNC int HPyCallable_Check(HPyContext *ctx, HPy h)
{
    return PyCallable_Check(_h2py(h));
}

HPyAPI_FUNC void HPyErr_SetString(HPyContext *ctx, HPy h_type, const char *message)
{
    PyErr_SetString(_h2py(h_type), message);
}

HPyAPI_FUNC void HPyErr_SetObject(HPyContext *ctx, HPy h_type, HPy h_value)
{
    PyErr_SetObject(_h2py(h_type), _h2py(h_value));
}

HPyAPI_FUNC HPy HPyErr_NoMemory(HPyContext *ctx)
{
    return _py2h(PyErr_NoMemory());
}

HPyAPI_FUNC void HPyErr_Clear(HPyContext *ctx)
{
    PyErr_Clear();
}

HPyAPI_FUNC HPy HPyErr_NewException(HPyContext *ctx, const char *name, HPy base, HPy dict)
{
    return _py2h(PyErr_NewException(name, _h2py(base), _h2py(dict)));
}

HPyAPI_FUNC HPy HPyErr_NewExceptionWithDoc(HPyContext *ctx, const char *name, const char *doc, HPy base, HPy dict)
{
    return _py2h(PyErr_NewExceptionWithDoc(name, doc, _h2py(base), _h2py(dict)));
}

HPyAPI_FUNC int HPy_IsTrue(HPyContext *ctx, HPy h)
{
    return PyObject_IsTrue(_h2py(h));
}

HPyAPI_FUNC HPy HPy_GetAttr(HPyContext *ctx, HPy obj, HPy name)
{
    return _py2h(PyObject_GetAttr(_h2py(obj), _h2py(name)));
}

HPyAPI_FUNC HPy HPy_GetAttr_s(HPyContext *ctx, HPy obj, const char *name)
{
    return _py2h(PyObject_GetAttrString(_h2py(obj), name));
}

HPyAPI_FUNC int HPy_HasAttr(HPyContext *ctx, HPy obj, HPy name)
{
    return PyObject_HasAttr(_h2py(obj), _h2py(name));
}

HPyAPI_FUNC int HPy_HasAttr_s(HPyContext *ctx, HPy obj, const char *name)
{
    return PyObject_HasAttrString(_h2py(obj), name);
}

HPyAPI_FUNC int HPy_SetAttr(HPyContext *ctx, HPy obj, HPy name, HPy value)
{
    return PyObject_SetAttr(_h2py(obj), _h2py(name), _h2py(value));
}

HPyAPI_FUNC int HPy_SetAttr_s(HPyContext *ctx, HPy obj, const char *name, HPy value)
{
    return PyObject_SetAttrString(_h2py(obj), name, _h2py(value));
}

HPyAPI_FUNC HPy HPy_GetItem(HPyContext *ctx, HPy obj, HPy key)
{
    return _py2h(PyObject_GetItem(_h2py(obj), _h2py(key)));
}

HPyAPI_FUNC int HPy_SetItem(HPyContext *ctx, HPy obj, HPy key, HPy value)
{
    return PyObject_SetItem(_h2py(obj), _h2py(key), _h2py(value));
}

HPyAPI_FUNC HPy HPy_Type(HPyContext *ctx, HPy obj)
{
    return _py2h(PyObject_Type(_h2py(obj)));
}

HPyAPI_FUNC HPy HPy_Repr(HPyContext *ctx, HPy obj)
{
    return _py2h(PyObject_Repr(_h2py(obj)));
}

HPyAPI_FUNC HPy HPy_Str(HPyContext *ctx, HPy obj)
{
    return _py2h(PyObject_Str(_h2py(obj)));
}

HPyAPI_FUNC HPy HPy_ASCII(HPyContext *ctx, HPy obj)
{
    return _py2h(PyObject_ASCII(_h2py(obj)));
}

HPyAPI_FUNC HPy HPy_Bytes(HPyContext *ctx, HPy obj)
{
    return _py2h(PyObject_Bytes(_h2py(obj)));
}

HPyAPI_FUNC HPy HPy_RichCompare(HPyContext *ctx, HPy v, HPy w, int op)
{
    return _py2h(PyObject_RichCompare(_h2py(v), _h2py(w), op));
}

HPyAPI_FUNC int HPy_RichCompareBool(HPyContext *ctx, HPy v, HPy w, int op)
{
    return PyObject_RichCompareBool(_h2py(v), _h2py(w), op);
}

HPyAPI_FUNC HPy_hash_t HPy_Hash(HPyContext *ctx, HPy obj)
{
    return PyObject_Hash(_h2py(obj));
}

HPyAPI_FUNC int HPyBytes_Check(HPyContext *ctx, HPy h)
{
    return PyBytes_Check(_h2py(h));
}

HPyAPI_FUNC HPy_ssize_t HPyBytes_Size(HPyContext *ctx, HPy h)
{
    return PyBytes_Size(_h2py(h));
}

HPyAPI_FUNC HPy_ssize_t HPyBytes_GET_SIZE(HPyContext *ctx, HPy h)
{
    return PyBytes_GET_SIZE(_h2py(h));
}

HPyAPI_FUNC char *HPyBytes_AsString(HPyContext *ctx, HPy h)
{
    return PyBytes_AsString(_h2py(h));
}

HPyAPI_FUNC char *HPyBytes_AS_STRING(HPyContext *ctx, HPy h)
{
    return PyBytes_AS_STRING(_h2py(h));
}

HPyAPI_FUNC HPy HPyBytes_FromString(HPyContext *ctx, const char *v)
{
    return _py2h(PyBytes_FromString(v));
}

HPyAPI_FUNC HPy HPyUnicode_FromString(HPyContext *ctx, const char *utf8)
{
    return _py2h(PyUnicode_FromString(utf8));
}

HPyAPI_FUNC int HPyUnicode_Check(HPyContext *ctx, HPy h)
{
    return PyUnicode_Check(_h2py(h));
}

HPyAPI_FUNC HPy HPyUnicode_AsUTF8String(HPyContext *ctx, HPy h)
{
    return _py2h(PyUnicode_AsUTF8String(_h2py(h)));
}

HPyAPI_FUNC HPy HPyUnicode_FromWideChar(HPyContext *ctx, const wchar_t *w, HPy_ssize_t size)
{
    return _py2h(PyUnicode_FromWideChar(w, size));
}

HPyAPI_FUNC int HPyList_Check(HPyContext *ctx, HPy h)
{
    return PyList_Check(_h2py(h));
}

HPyAPI_FUNC HPy HPyList_New(HPyContext *ctx, HPy_ssize_t len)
{
    return _py2h(PyList_New(len));
}

HPyAPI_FUNC int HPyList_Append(HPyContext *ctx, HPy h_list, HPy h_item)
{
    return PyList_Append(_h2py(h_list), _h2py(h_item));
}

HPyAPI_FUNC int HPyDict_Check(HPyContext *ctx, HPy h)
{
    return PyDict_Check(_h2py(h));
}

HPyAPI_FUNC HPy HPyDict_New(HPyContext *ctx)
{
    return _py2h(PyDict_New());
}

HPyAPI_FUNC int HPyTuple_Check(HPyContext *ctx, HPy h)
{
    return PyTuple_Check(_h2py(h));
}

HPyAPI_FUNC HPy HPyImport_ImportModule(HPyContext *ctx, const char *name)
{
    return _py2h(PyImport_ImportModule(name));
}
