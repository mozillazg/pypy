from collections import defaultdict

ITEM = object()

def namer():
    from itertools import count
    num = count()
    def make_name():
        for i in num:
            return '%%r%x' % (i,)
    return make_name

make_name = namer()


def index_name_maker(context, name):
    def aggregate_factory():
        return AggregateRegion(context, '%s[]' % (name,))
    return aggregate_factory


class Region(object):
    def __init__(self, context=None, name=None):
        self.context = context
        if name is not None:
            self.name = name
        else:
            self.name = make_name()
        self.indexes = defaultdict(index_name_maker(context, self.name))

    def get_item(self, index=ITEM):
        return self.indexes[index]

    def set_item(self, value, index=ITEM):
        self.indexes[index].add(value)

    def is_concrete(self, context):
        return True

    def is_abstract(self):
        return False

    def contents(self):
        return ()

    def __repr__(self):
        return self.name


class AbstractRegion(Region):
    def inside(self, context):
        # if the context is a child of the one this is on, we are already in
        # that context
        value = context.lookup_abstract_value(self)

        if value is not None:
            return value

        return self

    def is_concrete(self, context):
        value = context.lookup_abstract_value(self)
        return value is not None

    def contents(self):
        if self.context is not None:
            return [self.context.get_abstract_value(self)]
        return ()
            


class ConcreteRegion(Region):
    """A region refering to a known constant.

    Occasionally we know beforehand the entire value that the region
    will take, in the case of global constants and what not.
    """


class SemiConcreteRegion(Region):
    """A region referring to an object created on the domain of
    interest.

    A semi-concrete region is one that we know most of its secrets.
    Typically, a semi-concrete region will refer to all instances of
    an object created at a certain point.  We then use the call
    context to distinguish various paths an object can take.

    In this sense a region is semi-concrete; that together with a
    context, it can stand on its own and be absolutely disambiguated.
    """


class AggregateRegion(Region):
    def __init__(self, *args, **kwargs):
        self.regions = set()
        super(AggregateRegion, self).__init__(*args, **kwargs)

    def is_concrete(self, context):
        return False

    def contents(self):
        return self.regions

    def add(self, region):
        if region in self.regions:
            return
        self.regions.add(region)
        for index, value in self.indexes.iteritems():
            value.add(region.get_item(index))

    def get_item(self, index=ITEM):
        return super(AggregateRegion, self).get_item(index)

    def set_item(self, value, index=ITEM):
        super(AggregateRegion, self).set_item(value, index)


def distinct(x, y):
    return False


# XXX: use .contents() instead of an ugly type check
def separate_aggregates(regions):
    direct = set([r for r in regions if not isinstance(r, AggregateRegion)])
    refs = set([r for r in regions if isinstance(r, AggregateRegion)])
    return direct, refs


def flatten(regions):
    """Flatten a set of regions.

    Dataflow graphs typically generate AggregateRegions that refer to more
    AggregateRegions. flatten takes a set of regions and snaps pointers to
    others, and removes self-references.
    """

    # Unfortunately suboptimal in the case of higher-order cycles.
    # To be addressed.

    for region in regions:
        if not isinstance(region, AggregateRegion):
            continue
        if not any(isinstance(r, AggregateRegion) for r in region.regions):
            continue
        
        print '\nRegion:', region
        # region.regions will be built as a set containing only non-
        # aggregate references.
        #
        # refs_working is a set of references we have yet to deal with.
        #
        # refs_inlined is the set of references that have already been
        # dealt with.
        #
        # self_refs is a subset of refs_inlined that contains those that
        # are equal to this set.

        region.regions, refs_working = separate_aggregates(region.regions)
        refs_inlined = set([region])
        self_refs = set([region])

        while True:
            reference = refs_working.pop()
            refs_inlined.add(reference)
            new_regions, new_refs = separate_aggregates(reference.regions)
            if self_refs & reference.regions:
                # these sets contain each other => they are equal
                self_refs.add(reference)
                reference.regions = region.regions
            region.regions.update(new_regions)
            refs_working.update(new_refs - refs_inlined)
            if not refs_working:
                break



class RegionContext(object):
    """Distinguish concrete regions across call boundaries.

    if we had:

    def newlist():
        return []

    we would assign a semi concrete region to the new list so we could
    identify its origin.  However, that would not distinguish:

    def f():
        x = newlist()
        y = newlist()
        x.append(someregion)
        return y

    The region of the return value of f would be seen to be modified.
    So, we imbue function calls with a 'context', which will
    disabmiguate between these cases.

    Contexts can also distinguish usage across function call and loop
    boundaries, tightening the analysis further.  However, we do not
    track function applications yet and don't handle loops specially.
    """
    def __init__(self, parent_context=None):
        self.parent = parent_context
        self.bindings = {}

    def become(self, region, value):
        self.bindings[region] = value

    def get_abstract_value(self, abstract_region):
        return self.bindings[abstract_region]

    def lookup_abstract_value(self, abstract_region):
        while self is not None:
            try:
                return self.get_abstract_value(abstract_region)
            except KeyError:
                self = self.parent

    def aggregate_concreteness(self, aggregate_region):
        def visitor(region):
            if region.is_abstract():
                raise VisitException

        try:
            walk(aggregate_region, visitor)
        except VisitException:
            return False
        return True


class VisitException(Exception):
    pass


def walk(root, visitor):
    seen = set([root])
    working = set([root])

    while working:
        region = working.pop()
        remaining = seen.difference(region.contents())
        working.update(remaining)
        seen.update(remaining)
        visitor(region)


context = RegionContext
aggregate = AggregateRegion
concrete = ConcreteRegion
semiconcrete = SemiConcreteRegion
abstract = AbstractRegion
