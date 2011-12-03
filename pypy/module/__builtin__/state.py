
class State:
    def __init__(self, space):
        self.w_file = space.appexec([], """():
                import __builtin__file;
                return __builtin__file.file""")
        
def get(space):
    return space.fromcache(State)
