======================
Rawrefcount and the GC
======================


GC Interface
------------

"PyObject" is a raw structure with at least two fields, ob_refcnt and
ob_pypy_link.  The ob_refcnt is the reference counter as used on
CPython.  If the PyObject structure is linked to a live PyPy object,
its current address is stored in ob_pypy_link and ob_refcnt is bumped
by the constant REFCNT_FROM_PYPY_OBJECT.

rawrefcount_create_link_from_pypy(p, ob)

    Makes a link between an exising object gcref 'p' and a newly
    allocated PyObject structure 'ob'.  Both must not be linked so far.
    This adds REFCNT_FROM_PYPY_OBJECT to ob->ob_refcnt.

rawrefcount_create_link_to_pypy(p, ob)

    Makes a link from an existing PyObject structure 'ob' to a newly
    allocated W_CPyExtPlaceHolderObject 'p'.  The 'p' should have a
    back-reference field pointing to 'ob'.  This also adds
    REFCNT_FROM_PYPY_OBJECT to ob->ob_refcnt.

rawrefcount_from_obj(p)

    If there is a link from object 'p', and 'p' is not a
    W_CPyExtPlaceHolderObject, returns the corresponding 'ob'.
    Otherwise, returns NULL.

rawrefcount_to_obj(ob)

    Returns ob->ob_pypy_link, cast to a GCREF.


Collection logic
----------------

Objects existing purely on the C side have ob->ob_from_pypy == NULL;
these are purely reference counted.  On the other hand, if
ob->ob_from_pypy != NULL, then ob->ob_refcnt is at least
REFCNT_FROM_PYPY_OBJECT and the object is part of a "link".

The idea is that links whose 'p' is not reachable from other PyPy
objects *and* whose 'ob->ob_refcnt' is REFCNT_FROM_PYPY_OBJECT are the
ones who die.  But it is more messy because links created with
rawrefcount_create_link_to_pypy() need to have a deallocator called,
and this cannot occur immediately (and can do random things like
accessing other references this object points to, or resurrecting the
object).

Let P = list of links created with rawrefcount_create_link_from_pypy()
and O = list of links created with rawrefcount_create_link_to_pypy().
The PyPy objects in the list O are all W_CPyExtPlaceHolderObject: all
the data is in the PyObjects, and all references are regular
CPython-like reference counts.  It is the opposite with the P links:
all references are regular PyPy references from the 'p' object, and
the 'ob' is trivial.

So, after the collection we do this about P links:

    for (p, ob) in P:
        if ob->ob_refcnt != REFCNT_FROM_PYPY_OBJECT:
            mark 'p' as surviving, as well as all its dependencies

    for (p, ob) in P:
        if p is not surviving:
            unlink p and ob, free ob

Afterwards, the O links are handled like this:

    for (p, ob) in O:
        # p is trivial: it cannot point to other PyPy objects
        if p is not surviving:
            unlink p and ob
            ob->ob_refcnt -= REFCNT_FROM_PYPY_OBJECT
            if ob->ob_refcnt == 0:
                invoke _Py_Dealloc(ob) later, outside the GC


GC Implementation
-----------------

We need two P lists and two O lists, for young or old objects.  All
four lists can actually be linked lists of 'ob', using yet another
field 'ob_pypy_next'; or they can be regular AddressLists (unsure
about the overhead of this extra field for all PyObjects -- even ones
not linked to PyPy objects).

We also need an AddressDict mapping 'p' to 'ob' for all links in the P
list.  This dict contains both young and old 'p'; we simply write a
new entry when the object moves.  As a result it can contain some
extra garbage entries after some minor collections.  It is cleaned up
by being rebuilt at the next major collection.  We never walk all
items of that dict; we only walk the two explicit P lists.


Further notes
-------------

For small immutable types like <int> and <float>, we can actually
create a PyIntObject as a complete copy of the W_IntObject whenever
asked, and not record any link.  Is it cheaper?  Unclear.

A few special types need to be reflected both as PyPy objects and
PyObjects.  For now we assume that these are large and mostly
immutable, like <type> objects.  They should be linked in some mixture
of the P list and the O list.  Likely, the P list with an extra flag
that says "_Py_Dealloc must be invoked".
