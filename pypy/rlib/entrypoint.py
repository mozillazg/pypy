secondary_entrypoints = {}


def entrypoint(key, argtypes, c_name=None):
    def deco(func):
        secondary_entrypoints.setdefault(key, []).append((func, argtypes))
        if c_name is not None:
            func.c_name = c_name
        return func
    return deco

