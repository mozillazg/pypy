#!/usr/bin/env python 
import time
        
from pypy.lang.gameboy.gameboy import *
from pypy.lang.gameboy.joypad import JoypadDriver
from pypy.lang.gameboy.video import VideoDriver
from pypy.lang.gameboy.sound import SoundDriver


# GAMEBOY ----------------------------------------------------------------------

class GameBoyImplementation(GameBoy):
    
    def __init__(self):
        self.create_window()
        GameBoy.__init__(self)
        #self.mainLoop()
        
    def create_window(self):
        self.win = None
        #self.win = window.Window()
        #self.win.set_caption("PyBoy a GameBoy (TM)")
        pass
        
    def create_drivers(self):
        self.clock = Clock()
        self.joypad_driver = JoypadDriverImplementation(self.win)
        self.video_driver  = VideoDriverImplementation(self.win)
        self.sound_driver  = SoundDriverImplementation()
        
    def mainLoop(self):
        while not self.win.has_exit: 
            print "i"
            self.emulate(5)
            time.sleep(0.01)
        return 0
        
# VIDEO DRIVER -----------------------------------------------------------------

class VideoDriverImplementation(VideoDriver):
    
    def __init__(self, win):
        VideoDriver.__init__(self)
        #self.win = win
        #self.win.on_resize = self.on_resize
        #self.set_window_size()
        #self.create_image_buffer()

    def create_image_buffer(self):
        #self.buffers = image.get_buffer_manager()
        #self.image_buffer = self.buffers.get_color_buffer()
        #self.buffer_image_data = self.image_buffer.image_data
        #self.buffer_image_data.format = "RGB"
        #self.pixel_buffer = self.buffer_image_data.data
        pass
    
    def on_resize(self, width, height):
        pass
    
    def set_window_size(self):
        #self.win.set_size(self.width, self.height)
        pass
        
    def update_display(self):
        #self.buffer_image_data.data = map(self.pixel_to_byte, self.pixel_buffer)
        #self.image_buffer.blit(0, 0)
        #self.win.flip()
        pass
        
    def pixel_to_byte(self, int_number):
        return struct.pack("B", (int_number) & 0xFF, 
                                (int_number >> 8) & 0xFF, 
                                (int_number >> 16) & 0xFF)
        
        
# JOYPAD DRIVER ----------------------------------------------------------------

class JoypadDriverImplementation(JoypadDriver):
    
    def __init__(self, win):
        JoypadDriver.__init__(self)
        #self.create_button_key_codes()
        self.win = win
        #self.create_listeners()
        
    def create_button_key_codes(self):
        self.button_key_codes = {key.UP : (self.button_up),
                              key.RIGHT : (self.button_right), 
                              key.DOWN  : (self.button_down), 
                              key.LEFT  : (self.button_left), 
                              key.ENTER : (self.button_start),
                              key.SPACE : (self.button_select),
                              key.A     : (self.button_a), 
                              key.B     : (self.button_b)}
        
    def create_listeners(self):
        self.win.on_key_press = self.on_key_press
        self.win.on_key_release = self.on_key_press
        
    def on_key_press(self, symbol, modifiers): 
        pressButtonFunction = self.get_button_handler(symbol, modifiers)
        if pressButtonFunction is not None:
            pressButtonFunction(True)
    
    def on_key_release(self, symbol, modifiers): 
        pressButtonFunction = self.get_button_handler(symbol, modifiers)
        if pressButtonFunction is not None:
            pressButtonFunction(False)
            
    def get_button_handler(self, symbol, modifiers):
        if symbol in self.button_key_codes:
            if len(self.button_key_codes[symbol]) == 1 or\
                    self.button_key_codes[symbol][1] ==  modifiers:
                return self.button_key_codes[symbol][0]
        return None
        
        
# SOUND DRIVER -----------------------------------------------------------------

class SoundDriverImplementation(SoundDriver):
    
    def __init__(self):
        SoundDriver.__init__(self)
        self.create_sound_driver()
        self.enabled = True
        self.sampleRate = 44100
        self.channelCount = 2
        self.bitsPerSample = 8

    def create_sound_driver(self):
        pass
    
    def start(self):
        pass
        
    def stop(self):
        pass
    
    def write(self, buffer, length):
        pass
    
    
# ==============================================================================

def entry_point(args=None):
    gameboy = GameBoyImplementation()
    # add return statement...
    return 0


# _____ Define and setup target ___

def target(*args):
    return entry_point, None

if __name__ == '__main__':
    entry_point()