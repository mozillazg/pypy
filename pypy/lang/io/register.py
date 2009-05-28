from pypy.lang.io import model
cfunction_definitions = {}
def register_method(type_name, slot_name, unwrap_spec=None, alias=None):
    if alias is None:
        alias = [slot_name]
    else:
        alias.append(slot_name)
        
    def register(function):

        if unwrap_spec is None:
            wrapper = function
        else:
            def wrapper(space, w_target, w_message, w_context):
                evaled_w = [w_target]
                for i in range(len(unwrap_spec)-1):
                    evaled_w.append(
                        w_message.arguments[i].eval(
                            space, w_context, w_context))
                
                args = ()
                for x, typ in zip(evaled_w, unwrap_spec):
                    if typ is float:
                        assert isinstance(x, model.W_Number)
                        args += (x.value, )
                    elif typ is int:
                        assert isinstance(x, model.W_Number)
                        args += (int(x.value), )
                    elif typ is object:
                        args += (x, )
                    elif typ is str:
                        args += (x.value, )
                    elif typ is bool:
                        if x is space.w_true:
                            args += (True, )
                        else:
                            args += (False, )
                    else:
                        
                        raise ValueError, 'Unknown unwrap spec'
                return function(space, *args)
        subdict = cfunction_definitions.setdefault(type_name, {})

        
        for slotn in alias:
            subdict[slotn] = wrapper

        return function

    return register