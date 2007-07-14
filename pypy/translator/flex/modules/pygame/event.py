def get():
    return [Event() for x in range(2) ]
    
class Event:
    def __init__(self):
        self.type = 1
    