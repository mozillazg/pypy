# specialization support
import types

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
    from pypy.annotation.model import unionof
    # call the function now, and collect possible results
    func = funcdesc.pyobj
    if func is None:
        raise Exception("memo call: no Python function object to call (%r)" %
                        (funcdesc,))
    possible_results = []
    for arglist in possible_arguments(arglist_s):
        result = func(*arglist)
        possible_results.append(funcdesc.bookkeeper.immutablevalue(result))
    return unionof(*possible_results)

def possible_values_of(s):
    from pypy.annotation.model import SomeBool, SomePBC
    if s.is_constant():
        return [s.const]
    elif isinstance(s, SomePBC):
        result = []
        for desc in s.descriptions:
            if desc.pyobj is None:
                raise Exception("memo call with a PBC that has no "
                                "corresponding Python object (%r)" % (desc,))
            result.append(desc.pyobj)
        return result
    elif isinstance(s, SomeBool):
        return [False, True]
    else:
        raise ValueError, "memo call with a non-constant arg %r" % (s,)

def possible_arguments(args):
    # enumerate all tuples (x1,..xn) of concrete values that are contained
    # in a tuple args=(s1,..sn) of SomeXxx.  Requires that each s be either
    # a constant or SomePBC.
    return cartesian_product([possible_values_of(s) for s in args])

def cartesian_product(lstlst):
    if not lstlst:
        yield ()
        return
    for tuple_tail in cartesian_product(lstlst[1:]):
        for value in lstlst[0]:
            yield (value,) + tuple_tail

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
