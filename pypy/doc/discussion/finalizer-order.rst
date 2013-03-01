Ordering finalizers in the MiniMark GC
======================================


Goal
----

After a collection, the MiniMark GC should call the finalizers on *some*
of the objects that have one and that have become unreachable.

It used to be that if there is a reference from ``a`` to ``b``, both of
which have a finalizer, then only the finalizer of ``a`` was called.
The object ``b`` would simply stay around and, if nothing changed, have
its finalizer called at the next major collection.

However, this creates rare but annoying issues as soon as the program
creates chains of objects with finalizers more quickly than the rate at
which major collections go (which is very slow).

After discussion with python-dev it was found reasonable to try instead
to call all finalizers of all objects found unreachable at a major
collection.  More precisely, if ``a`` has a reference to ``b`` and they
both are found to be unreachable from outside, then (of course, as
before) neither ``a`` nor ``b`` is immediately freed, but we queue the
execution of the finalizer for ``a`` and ``b``, in that order.  As a
result, the finalizer for ``b`` will be called even if the finalizer for
``a``, running before, does any change to the object graph that causes
``b`` to be resurrected.


RPython interface
-----------------

In RPython programs like PyPy, we need a finer-grained method of
controlling the RPython- as well as the app-level ``__del__()``.
To make it possible, the RPython interface is now the following one:

* RPython objects can have ``__del__()``.  These are called immediately
  by the GC when the last reference to the object goes away, like in
  CPython.  However (like "lightweight finalizers" used to be), all
  ``__del__()`` methods must only contain simple enough code, and this
  is checked.

* For any more advanced usage --- in particular for any app-level object
  with a __del__ --- we don't use the RPython-level ``__del__()``
  method.  Instead we use ``rgc.register_finalizer()``.  The finalizer
  that we attach gives more control over the ordering than just an
  RPython ``__del__()``.


Lightweight finalizers
----------------------

A lightweight finalizer is an RPython ``__del__()`` method that is
called directly by the GC when there is no more reference to an object
(including from other objects with finalizers).  Intended for objects
that just need to free a block of raw memory or close a file.

There are restrictions on the kind of code you can put in ``__del__()``,
including all other functions called by it.  These restrictions are
checked.  In particular you cannot access fields containing GC objects;
and if you call an external C function, it must be a "safe" function.
(XXX check/implement this)


Register_finalizer
------------------

The interface is made with PyPy in mind, but should be generally useful.

``rgc.register_finalizer(obj, finalizer_function)``

   After a major collection, the GC finds all objects ``obj`` on which a
   finalizer was registered and which are unreachable, and mark them as
   reachable again, as well as all objects they depend on.  It then
   picks a topological ordering (breaking cycles randomly) and enqueues
   the objects and their registered finalizer functions in that order.
   Finally, when the major collection is done, it calls
   ``rgc.progress_through_finalizer_queue()`` once, unless there is
   already a call to ``rgc.progress_through_finalizer_queue()`` in
   progress.

``rgc.progress_through_finalizer_queue()``

   This function calls ``finalizer_function(obj)`` for the objects in
   the queue, in order.  The progression through the queue is interrupted
   when one function raises ``rgc.FinalizeLater``; in that case, this
   function remains at the front of the queue, and will be called again
   by the next call to ``progress_through_finalizer_queue()``.

The idea is that the finalizer functions in PyPy either do their clean-up
immediately (for the case where they are not lightweight finalizers, but
don't require synchronization), or are postponed to be executed at the
end of the current bytecode by the interpreter.  This is done by writing
such functions with this logic::

    def finalize(self):
        ec = self.space.getexecutioncontext()
        if not ec.running_finalizers:
            ec.schedule_later_call_to_progress_through_finalizer_queue()
            raise FinalizeLater
        else:
            # real logic, which occurs between bytecodes


How the GC orders the queue: algorithm
--------------------------------------

XXXX



During deal_with_objects_with_finalizers(), each object x can be in 4
possible states::

    state[x] == 0:  unreachable
    state[x] == 1:  (temporary state, see below)
    state[x] == 2:  reachable from any finalizer
    state[x] == 3:  alive

Initially, objects are in state 0 or 3 depending on whether they have
been copied or not by the regular sweep done just before.  The invariant
is that if there is a reference from x to y, then state[y] >= state[x].

The state 2 is used for objects that are reachable from a finalizer but
that may be in the same strongly connected component than the finalizer.
The state of these objects goes to 3 when we prove that they can be
reached from a finalizer which is definitely not in the same strongly
connected component.  Finalizers on objects with state 3 must not be
called.

Let closure(x) be the list of objects reachable from x, including x
itself.  Pseudo-code (high-level) to get the list of marked objects::

    marked = []
    for x in objects_with_finalizers:
        if state[x] != 0:
            continue
        marked.append(x)
        for y in closure(x):
            if state[y] == 0:
                state[y] = 2
            elif state[y] == 2:
                state[y] = 3
    for x in marked:
        assert state[x] >= 2
        if state[x] != 2:
            marked.remove(x)

This does the right thing independently on the order in which the
objects_with_finalizers are enumerated.  First assume that [x1, .., xn]
are all in the same unreachable strongly connected component; no object
with finalizer references this strongly connected component from
outside.  Then:

* when x1 is processed, state[x1] == .. == state[xn] == 0 independently
  of whatever else we did before.  So x1 gets marked and we set
  state[x1] = .. = state[xn] = 2.

* when x2, ... xn are processed, their state is != 0 so we do nothing.

* in the final loop, only x1 is marked and state[x1] == 2 so it stays
  marked.

Now, let's assume that x1 and x2 are not in the same strongly connected
component and there is a reference path from x1 to x2.  Then:

* if x1 is enumerated before x2, then x2 is in closure(x1) and so its
  state gets at least >= 2 when we process x1.  When we process x2 later
  we just skip it ("continue" line) and so it doesn't get marked.

* if x2 is enumerated before x1, then when we process x2 we mark it and
  set its state to >= 2 (before x2 is in closure(x2)), and then when we
  process x1 we set state[x2] == 3.  So in the final loop x2 gets
  removed from the "marked" list.

I think that it proves that the algorithm is doing what we want.

The next step is to remove the use of closure() in the algorithm in such
a way that the new algorithm has a reasonable performance -- linear in
the number of objects whose state it manipulates::

    marked = []
    for x in objects_with_finalizers:
        if state[x] != 0:
            continue
        marked.append(x)
        recursing on the objects y starting from x:
            if state[y] == 0:
                state[y] = 1
                follow y's children recursively
            elif state[y] == 2:
                state[y] = 3
                follow y's children recursively
            else:
                don't need to recurse inside y
        recursing on the objects y starting from x:
            if state[y] == 1:
                state[y] = 2
                follow y's children recursively
            else:
                don't need to recurse inside y
    for x in marked:
        assert state[x] >= 2
        if state[x] != 2:
            marked.remove(x)

In this algorithm we follow the children of each object at most 3 times,
when the state of the object changes from 0 to 1 to 2 to 3.  In a visit
that doesn't change the state of an object, we don't follow its children
recursively.

In practice, in the SemiSpace, Generation and Hybrid GCs, we can encode
the 4 states with a single extra bit in the header:

      =====  =============  ========  ====================
      state  is_forwarded?  bit set?  bit set in the copy?
      =====  =============  ========  ====================
        0      no             no        n/a
        1      no             yes       n/a
        2      yes            yes       yes
        3      yes          whatever    no
      =====  =============  ========  ====================

So the loop above that does the transition from state 1 to state 2 is
really just a copy(x) followed by scan_copied().  We must also clear the
bit in the copy at the end, to clean up before the next collection
(which means recursively bumping the state from 2 to 3 in the final
loop).

In the MiniMark GC, the objects don't move (apart from when they are
copied out of the nursery), but we use the flag GCFLAG_VISITED to mark
objects that survive, so we can also have a single extra bit for
finalizers:

      =====  ==============  ============================
      state  GCFLAG_VISITED  GCFLAG_FINALIZATION_ORDERING
      =====  ==============  ============================
        0        no              no
        1        no              yes
        2        yes             yes
        3        yes             no
      =====  ==============  ============================
