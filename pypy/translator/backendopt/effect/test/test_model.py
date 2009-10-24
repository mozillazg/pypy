from pypy.translator.backendopt.effect.model import distinct, context, \
    abstract, semiconcrete, concrete, flatten, aggregate

class TestCanRaise(object):

    def test_semiconcrete_distinct(self):
        "unique semiconcrete regions are distinct"
        self.semiconcrete_distinct(semiconcrete(), semiconcrete())

    def semiconcrete_distinct(self, x, y):
        assert distinct(x, y)
        assert not distinct(x, x)

    def test_semiconcrete_distinct_contexts(self):
        "unique semiconcrete regions are distinct in their context"
        self.semiconcrete_distinct_contexts(semiconcrete(), semiconcrete())

    def semiconcrete_distinct_contexts(self, x, y):
        assert distinct(x, y)
        assert not distinct(x, x)

        context0 = context()
        context1 = context()
        assert distinct(x.inside(context0), x.inside(context1))
        assert distinct(x.inside(context0), y.inside(context0))
        assert not distinct(x.inside(context0), x.inside(context0))

    def test_abstract_nondistinct(self):
        "unless they have different type, abstract regions are not distinct"
        x = abstract()
        y = abstract()

        assert not distinct(x, y)
        assert not distinct(x, x)

    def test_abstract_become(self):
        "abstract regions may become concrete or semiconcrete"
        x = abstract()
        y = abstract()

        specialisation_context = context()

        specialisation_context.become(x, semiconcrete())

        assert not distinct(x.inside(specialisation_context), y)

        specialisation_context.become(x, semiconcrete())

        assert distinct(x.inside(specialisation_context),
                        y.inside(specialisation_context))

        specialisation_context = context()
        some_concrete = semiconcrete()

        specialisation_context.become(x, some_concrete)
        assert not distinct(x.inside(specialisation_context), y)
        
        specialisation_context.become(y, some_concrete)
        assert not distinct(x.inside(specialisation_context),
                            y.inside(specialisation_context))

    def test_abstract_semiconcrete(self):
        """The distinctness of semiconcrete and abstract may be
        glorked from context.

        That is to say, the regions that are abstract and concrete in a
        given context are distinct.  This is because a region cannot both
        come from inside and outside the function call.

        Actually, this is not true, the concrete region could have
        been passed to some other function, and the abstract region is
        the retun value of the function.

        shrug.
        """

        x = abstract()
        specialisation_context = context()
        y = semiconcrete(context=specialisation_context)

        assert distinct(x, y)

        assert not distinct(x.inside(specialisation_context),
                            y.inside(specialisation_context))


    def test_index(self):
        r1 = concrete()
        r2 = concrete()

        w, x, y, z = [concrete() for _ in xrange(4)]
        r1.set_item(w)
        r1.set_item(x)
        r2.set_item(y)
        r2.set_item(z)

        assert distinct(r1.get_item(), r2.get_item())

        r1.set_item(y)

        assert not distinct(r1.get_item(), r2.get_item())

    def test_attr(self):
        r1 = concrete()
        r2 = concrete()

        w, x, y, z = [concrete() for _ in xrange(4)]
        r1.set_item(w, 'w')
        r1.set_item(x, 'w')
        r2.set_item(w, 'w')
        r2.set_item(x, 'x')

        assert distinct(r2.get_item('x'), r2.get_item('w'))
        assert distinct(r1.get_item('x'), r2.get_item('x'))
        assert not distinct(r1.get_item('w'), r2.get_item('w'))

    def test_aggregates(self):
        x = aggregate()
        y = aggregate([x])
        z = aggregate([y])
        x.add(z)

        flatten([x])

        assert distinct(x, abstract())

        c = concrete()
        x = aggregate([c])
        y = aggregate([x])
        z = aggregate([y])
        x.add(z)

        flatten([x])
        
        assert not distinct(x, c)
        assert x.regions == y.regions == z.regions

        c = concrete()
        y.add(c)

        assert len(x.regions) == 2
