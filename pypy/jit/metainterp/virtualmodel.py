
def declare_virtual(cls):
    class Virtual(cls):
        def force(self, optimizer):
            if not self._isforced:
                optimizer.emit_operation(self)
                self._isforced = True
            return self
        
        def is_virtual(self):
            return not self._isforced
    return Virtual
