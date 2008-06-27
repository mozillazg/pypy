
enabled = [True]

def isenabled():
    return enabled[0]

def enable():
    import gc
    if not enabled[0]:
        gc.enable_finalizers()
        enabled[0] = True

def disable():
    import gc
    if enabled[0]:
        gc.disable_finalizers()
        enabled[0] = False
