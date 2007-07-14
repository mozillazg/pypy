import pygame

class Font:
    def __init__(self, fontfile, size):
        self.size = size
        
        
    def render(self, text, alpha, color):
        return pygame.Surface( (len(text)*self.size, self.size) )