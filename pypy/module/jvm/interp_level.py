def hello(space, w_name):
    res = "Hello, {0}, this is interp-level!".format(space.str_w(w_name))
    return space.wrap(res)
