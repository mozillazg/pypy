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


How the GC orders the queue
---------------------------

In two words:

``register_finalizer`` sets the flag GCFLAG_HAS_FINALIZER, and records
the finalizer in a dictionary.

At the end of a major collection, walk the list of objects with a
finalizer.  For each one that is not reachable, do a depth-first search
to mark everything that it depends on as "surviving".  The depth-first
search algo is written in such a way that it builds a list of exactly
those objects found with GCFLAG_HAS_FINALIZER --- in topological order.

Algorithm::

    for obj in unreachable_objects_with_finalizer:

        if (obj.flag & GCFLAG_HAS_FINALIZER) == 0:
            continue    # already queued, in 'finalizer_queue'

        pending = Stack([obj])

        while pending.not_empty():
            obj = pending.pop()

            if obj is actually a MARKER(obj'):
                finalizer_queue.append(obj')
                continue

            make sure obj is not freed during this major collection

            if obj.flag & GCFLAG_HAS_FINALIZER:
                obj.flag -= GCFLAG_HAS_FINALIZER
                pending.append(MARKER(obj))

            trace 'obj' and add to 'pending' all references not seen so far
