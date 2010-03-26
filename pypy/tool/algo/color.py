
class DependencyGraph(object):
    """ A dependency graph for a given control flow graph (CFG).

    Each variable is an node in a graph and we have an edge
    if two variables are alive at the same point of time

    the whole algorithm is based on the following paper:
    http://citeseerx.ist.psu.edu/viewdoc/download?doi=10.1.1.86.1578&rep=rep1&type=pdf
    """
