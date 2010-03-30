secondary_entrypoints = {}


def entrypoint(key, argtypes, c_name=None, relax=False):
    def deco(func):
        secondary_entrypoints.setdefault(key, []).append((func, argtypes))
        if c_name is not None:
            func.c_name = c_name
        if relax:
            func.relax_sig_check = True
        return func
    return deco

