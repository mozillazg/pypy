from functools import wraps

class SkipArgument(Exception): pass

class CallLogger(object):
    def __init__(self):
        self.indentation = 0
    
    def format_arg(self, arg, args=[], kwargs={}, name=''):
        return repr(arg)

    def argstrs(self, args, kwargs):
        argstrs = []
        for arg in args:
            try:
                argstrs.append(self.format_arg(arg, args, kwargs))
            except SkipArgument, e: continue
        argstr = ', '.join(argstrs)

        kwargstrs = []
        for name, arg in kwargs.iteritems():
            try:
                kwargstrs.append("%s=%s" % (name, self.format_arg(arg, args, kwargs, name=name)))
            except SkipArgument, e: continue
        kwargstr = ', '.join(kwargstrs)

        if argstr and kwargstr:
            return ', '.join([argstr, kwargstr])
        elif argstr:
            return argstr
        else:
            return kwargstr

    def log(self, logstr, depth=0):
        print (' ' * depth) + logstr

    def log_call(self, f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            argstr = self.argstrs(args, kwargs)
            self.log("%s(%s)" % (f.__name__, argstr), depth=self.indentation)
            self.indentation += 1
            result = f(*args, **kwargs)
            self.indentation -= 1
            self.log("%s(%s)->%r" % (f.__name__, argstr, result), depth=self.indentation)
            return result
        return wrapped
