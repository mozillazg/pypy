# specialization support
import types
from pypy.tool.uid import uid

def default_specialize(funcdesc, args_s):
    argnames, vararg, kwarg = funcdesc.signature
    assert not kwarg, "functions with ** arguments are not supported"
    if vararg:
        from pypy.annotation import model as annmodel
        # calls to *arg functions: create one version per number of args
        assert len(args_s) == len(argnames) + 1
        s_tuple = args_s[-1]
        assert isinstance(s_tuple, annmodel.SomeTuple), (
            "calls f(..., *arg) require 'arg' to be a tuple")
        s_len = s_tuple.len()
        assert s_len.is_constant(), "calls require known number of args"
        nb_extra_args = s_len.const
        return funcdesc.cachedgraph(nb_extra_args)
    else:
        return funcdesc.cachedgraph(None)

# ____________________________________________________________________________
# specializations

def memo(funcdesc, arglist_s):
    """NOT_RPYTHON"""
    from pypy.annotation.model import unionof, SomePBC, SomeImpossibleValue
    # call the function now, and collect possible results
    func = funcdesc.pyobj
    if func is None:
        raise Exception("memo call: no Python function object to call (%r)" %
                        (funcdesc,))
    if len(arglist_s) != 1:
        raise Exception("memo call: only one-argument functions supported"
                        " at the moment (%r)" % (funcdesc,))
    s = arglist_s[0]
    if not isinstance(s, SomePBC):
        if isinstance(s, SomeImpossibleValue):
            return s    # we will probably get more possible args later
        raise Exception("memo call: argument must be a class or a frozen PBC,"
                        " got %r" % (s,))
    # compute the concrete result and store them directly on the descs,
    # using a strange attribute name
    attrname = '$memo_%s_%d' % (funcdesc.name, uid(funcdesc))
    for desc in s.descriptions:
        s_result = desc.s_read_attribute(attrname)
        if isinstance(s_result, SomeImpossibleValue):
            # first time we see this 'desc'
            if desc.pyobj is None:
                raise Exception("memo call with a class or PBC that has no "
                                "corresponding Python object (%r)" % (desc,))
            result = func(desc.pyobj)
            s_result = funcdesc.bookkeeper.immutablevalue(result)
            desc.create_new_attribute(attrname, result)
    # get or build the graph of the function that reads this strange attr
    def memoized(x):
        return getattr(x, attrname)
    return funcdesc.cachedgraph('memo', memoized, 'memo_%s' % funcdesc.name)


def argvalue(i):
    def specialize_argvalue(funcdesc, args_s):
        key = args_s[i].const
        return funcdesc.cachedgraph(key)        
    return specialize_argvalue

def argtype(i):
    def specialize_argtype(funcdesc, args_s):
        key = args_s[i].knowntype
        return funcdesc.cachedgraph(key)        
    return specialize_argtype
