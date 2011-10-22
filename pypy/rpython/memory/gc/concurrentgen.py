"""
************************************************************
  Minor collection cycles of the "concurrentgen" collector
************************************************************


Objects mark byte:

    cym in 'mK': young objs (and all flagged objs)
    cam in 'Km': aging objs
    '#'        : old objs
    'S'        : static prebuilt objs with no heap pointer

'cym' is the current young marker
'cam' is the current aging marker

The write barrier activates when writing into an object whose
mark byte is different from 'cym'.


------------------------------------------------------------

Step 1.  Only the mutator runs.

   old obj    flagged obj     old obj
                    |
                    |
                    v
                young obj...

Write barrier: change "old obj" to "flagged obj"
    (if mark != cym:
         mark = cym (used to be '#' or 'S')
         record the object in the "flagged" list)
    - note that we consider that flagged old objs are again young objects

------------------------------------------------------------

Step 2.  Preparation of running the collector.  (Still single-threaded.)

   - young objs -> aging objs
         (exchange the values of 'cam' and 'cym'.
          there was no 'cam' object, so now there is no 'cym' object)

   - collect roots; add roots and flagged objs to the "gray objs" list

   - unflag objs (i.e. empty the "flagged" list)

------------------------------------------------------------

Step 3.  Parallel execution of the collector, mark phase

   old obj    old obj     old obj

         aging obj   aging obj

   new young obj...


Collector thread:

    for each gray obj:
        skip obj if not an aging obj    (i.e. if mark != cam: continue)
        for each obj found by tracing:
            add to gray objs      (if not an aging obj, will be skipped later)
        gray obj -> black obj     (i.e. mark = '#')

Write barrier:

   - perform as a "deletion barrier", detecting changes done to aging objs
        (i.e. if mark == cam,
                  mark = '#'
                  trace and add to gray objs)
   - also flag old-or-aging objs that point to new young objs
        (if mark != cym:
             mark = cym (used to be '#' or 'S')
             record the object in the "flagged" list)

Threading issues:

   - it's possible that both threads will trace the same object, if we're
     unlucky, but it does not have buggy effects
   - the "mark = '#'" in the collector thread can conflict with the
     "mark = cym" in the mutator write barrier, but again, it should not
     have buggy effects beyond occasionally triggering the write barrier
     twice on the same object, adding it twice in "flagged" (and never more)
   - it is essential to have "mark = '#'" _after_ tracing in the collector
     thread; otherwise, the write barrier in the mutator thread would be
     ignored in case it occurs between the two, and then the tracing done
     by the collector thread doesn't see the original values any more.
   - the detection of "we are done" in the collector thread needs to
     account for the write barrier currently tracing and adding more
     objects to "gray objs".

------------------------------------------------------------

Step 4.  Parallel execution of the collector, sweep phase

    for obj in previous nursery:
        if obj is "black":     (i.e. if mark != cam)
            make the obj old   (         nothing to do here, mark already ok)
        else:
            clear the object space and return it to the available list
    after this there are no more aging objects

Write barrier:

   - flag old objs that point to new young objs
        (should not see any 'cam' object any more here)

------------------------------------------------------------
"""
