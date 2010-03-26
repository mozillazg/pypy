
class DependencyGraph(object):
    """ A dependency graph for a given control flow graph (CFG).

    Each variable is an node in a graph and we have an edge
    if two variables are alive at the same point of time
    """
