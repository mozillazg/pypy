import java.io.InputStream;
import java.lang.annotation.Annotation;
import java.lang.reflect.*;
import java.net.URL;
import java.security.ProtectionDomain;

public class RjvmJavaClassWrapper {
    private Class<?> klass;

    public <U> Class<? extends U> asSubclass(Class<U> clazz) {
        return klass.asSubclass(clazz);
    }

    public Object[] getSigners() {
        return klass.getSigners();
    }

    public boolean isSynthetic() {
        return klass.isSynthetic();
    }

    public int getModifiers() {
        return klass.getModifiers();
    }

    public Field getField(String name) throws NoSuchFieldException, SecurityException {
        return klass.getField(name);
    }

    public boolean isLocalClass() {
        return klass.isLocalClass();
    }

    public Field[] getFields() throws SecurityException {
        return klass.getFields();
    }

    public Class<?> getEnclosingClass() {
        return klass.getEnclosingClass();
    }

    public boolean isPrimitive() {
        return klass.isPrimitive();
    }

    public Class<?> getSuperclass() {
        return klass.getSuperclass();
    }

    public boolean isAnnotation() {
        return klass.isAnnotation();
    }

    public ProtectionDomain getProtectionDomain() {
        return klass.getProtectionDomain();
    }

    public TypeVariable[] getTypeParameters() {
        return klass.getTypeParameters();
    }

    public Class<?>[] getDeclaredClasses() throws SecurityException {
        return klass.getDeclaredClasses();
    }

    public InputStream getResourceAsStream(String name) {
        return klass.getResourceAsStream(name);
    }

    public Annotation[] getAnnotations() {
        return klass.getAnnotations();
    }

    public Method getDeclaredMethod(String name, Class<?>... parameterTypes) throws NoSuchMethodException, SecurityException {
        return klass.getDeclaredMethod(name, parameterTypes);
    }

    public Constructor<?>[] getConstructors() throws SecurityException {
        return klass.getConstructors();
    }

    public Constructor<?> getConstructor(Class<?>... parameterTypes) throws NoSuchMethodException, SecurityException {
        return klass.getConstructor(parameterTypes);
    }

    public Annotation[] getDeclaredAnnotations() {
        return klass.getDeclaredAnnotations();
    }

    public Method getMethod(String name, Class<?>... parameterTypes) throws NoSuchMethodException, SecurityException {
        return klass.getMethod(name, parameterTypes);
    }

    public boolean isAssignableFrom(Class<?> cls) {
        return klass.isAssignableFrom(cls);
    }

    public Constructor<?> getDeclaredConstructor(Class<?>... parameterTypes) throws NoSuchMethodException, SecurityException {
        return klass.getDeclaredConstructor(parameterTypes);
    }

    public boolean isEnum() {
        return klass.isEnum();
    }

    public Class<?>[] getClasses() {
        return klass.getClasses();
    }

    public Method[] getMethods() throws SecurityException {
        return klass.getMethods();
    }

    public Class<?>[] getInterfaces() {
        return klass.getInterfaces();
    }

    public ClassLoader getClassLoader() {
        return klass.getClassLoader();
    }

    public Field getDeclaredField(String name) throws NoSuchFieldException, SecurityException {
        return klass.getDeclaredField(name);
    }

    public URL getResource(String name) {
        return klass.getResource(name);
    }

    public Class<?> getDeclaringClass() {
        return klass.getDeclaringClass();
    }

    public boolean isArray() {
        return klass.isArray();
    }

    public Field[] getDeclaredFields() throws SecurityException {
        return klass.getDeclaredFields();
    }

    public boolean isAnnotationPresent(Class<? extends Annotation> annotationClass) {
        return klass.isAnnotationPresent(annotationClass);
    }

    public String getCanonicalName() {
        return klass.getCanonicalName();
    }

    public String getName() {
        return klass.getName();
    }

    public Class<?> getComponentType() {
        return klass.getComponentType();
    }

    public static RjvmJavaClassWrapper forName(String className) throws ClassNotFoundException {
        return new RjvmJavaClassWrapper(Class.forName(className));
    }

    public Object cast(Object obj) {
        return klass.cast(obj);
    }

    public boolean isInstance(Object obj) {
        return klass.isInstance(obj);
    }

    public Constructor<?>[] getDeclaredConstructors() throws SecurityException {
        return klass.getDeclaredConstructors();
    }

    public Type getGenericSuperclass() {
        return klass.getGenericSuperclass();
    }

    public boolean isAnonymousClass() {
        return klass.isAnonymousClass();
    }

    public Type[] getGenericInterfaces() {
        return klass.getGenericInterfaces();
    }

    public Method getEnclosingMethod() {
        return klass.getEnclosingMethod();
    }

    public boolean desiredAssertionStatus() {
        return klass.desiredAssertionStatus();
    }

    public Package getPackage() {
        return klass.getPackage();
    }

    public boolean isInterface() {
        return klass.isInterface();
    }

    public Constructor<?> getEnclosingConstructor() {
        return klass.getEnclosingConstructor();
    }

    public String getSimpleName() {
        return klass.getSimpleName();
    }

    public Object newInstance() throws InstantiationException, IllegalAccessException {
        return klass.newInstance();
    }

    public static Class<?> forName(String name, boolean initialize, ClassLoader loader) throws ClassNotFoundException {
        return Class.forName(name, initialize, loader);
    }

    public <A extends Annotation> A getAnnotation(Class<A> annotationClass) {
        return klass.getAnnotation(annotationClass);
    }

    public Method[] getDeclaredMethods() throws SecurityException {
        return klass.getDeclaredMethods();
    }

    public boolean isMemberClass() {
        return klass.isMemberClass();
    }

    public RjvmJavaClassWrapper(Class<?> klass) {
        this.klass = klass;
    }
}
