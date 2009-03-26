cfunction_definitions = {}
def register_method(type_name, slot_name):
    def register(function):
        subdict = cfunction_definitions.setdefault(type_name, {})
        subdict[slot_name] = function
        return function
    return register