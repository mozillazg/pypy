
def init():
    pass

class Rect:
    pass
    
class Surface:
    def __init__(self, size):
        self.size = size
        
    def convert(self):
        return Surface(self.size)
        
    def fill(self, color):
        pass
        
    def blit(self, surface, position):
        pass
    blit._annspecialcase_ = 'specialize:argtype(2)'    
    
    def get_size(self):
        return self.size
        
    def get_rect(self, centerx=1):
        return Rect()
        
    def get_width(self):
        return self.size[0]
        
    def get_at(self, position):
        return (100,100,100)
        
    def set_colorkey(self, colorkey, options):
        pass
        
        
        

        
        
class Display:
    def get_surface(self):
        return Surface((10,10))
        
    def set_mode(self, (x, y)):
        return Surface((x,y))
        
    def set_caption(self, caption):
        pass

    def flip(self):
        pass
        
    def get_rect(self):
        pass
            
display = Display()

class Mouse:
    def set_visible(self, bool):
        pass
    
mouse = Mouse()

