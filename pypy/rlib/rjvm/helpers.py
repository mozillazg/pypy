import jpype
import api

RjvmJavaLangClassWrapper = jpype.JClass('RjvmJavaClassWrapper')
JPypeJavaClass = type(jpype.java.lang.String.__javaclass__)

def _is_static(method_or_field):
    return jpype.java.lang.reflect.Modifier.isStatic(method_or_field.getModifiers())

def _is_public(method_or_field):
    return jpype.java.lang.reflect.Modifier.isPublic(method_or_field.getModifiers())

def _get_fields(refclass, static=False):
    staticness = _check_staticness(static)
    return [f for f in refclass.getFields() if staticness(f) and _is_public(f)]

def _get_methods(refclass, static=False):
    staticness = _check_staticness(static)
    return [m for m in refclass.getMethods() if staticness(m) and _is_public(m)]

def _check_staticness(should_be_static):
    if should_be_static:
        return _is_static
    else:
        return lambda m: not _is_static(m)

def _refclass_for(o):
    """
    Get the appropriate instance of java.lang.Class for objects of various
    types that show up in RJVM code. refclass stands for "reflection-level class".
    """
    if isinstance(o, RjvmJavaLangClassWrapper):
        return o
    elif isinstance(o, api.JvmClassWrapper):
        return o.__refclass__
    elif isinstance(o, api.JvmInstanceWrapper):
        if isinstance(o.__wrapped__, RjvmJavaLangClassWrapper):
            return RjvmJavaLangClassWrapper.java_lang_Class
        else:
            return _refclass_for(o.__wrapped__)
    elif isinstance(o, JPypeJavaClass):
        return RjvmJavaLangClassWrapper.forName(o.getName())
    elif hasattr(o, '__javaclass__'):
        return _refclass_for(o.__javaclass__)
    else:
        raise TypeError("Bad type for tpe!")

reflection_exceptions = {'java.lang.ClassNotFoundException',
                         'java.lang.reflect.InvocationTargetException',
                         'java.lang.NoSuchMethodException',
                         'java.lang.NoSuchFieldException', }

def handle_java_exception(e):
    """
    This 'hack' forces the interpreted code to behave like the compiled code
    with regards to reflection exceptions.
    """
    if e.javaClass().__name__ in reflection_exceptions:
        raise api.ReflectionException
    else:
        raise
