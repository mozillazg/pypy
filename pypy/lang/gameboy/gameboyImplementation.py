#!/usr/bin/env python 
import time
        
from pypy.lang.gameboy.gameboy import GameBoy
from pypy.lang.gameboy.joypad import JoypadDriver
from pypy.lang.gameboy.video import VideoDriver
from pypy.lang.gameboy.sound import SoundDriver
from pypy.rlib.rsdl import RSDL, RSDL_helper


# GAMEBOY ----------------------------------------------------------------------

class GameBoyImplementation(GameBoy):
    
    def __init__(self):
        GameBoy.__init__(self)
        self.init_sdl()
        #self.mainLoop()
        
    def init_sdl(self):
        assert RSDL.Init(RSDL.INIT_VIDEO) >= 0
        self.event = lltype.malloc(RSDL.Event, flavor='raw')

    def create_window(self):
        self.win = None
        #self.win = window.Window()
        #self.win.set_caption("PyBoy a GameBoy (TM)")
        pass
        
    def create_drivers(self):
        self.clock = Clock()
        self.joypad_driver = JoypadDriverImplementation()
        self.video_driver  = VideoDriverImplementation()
        self.sound_driver  = SoundDriverImplementation()
        
    def mainLoop(self):
        try:
            while not self.win.has_exit:
                self.joypad_driver.update( self.event) 
                self.emulate(5)
                time.sleep(0.01)
        finally:
            lltype.free(event, flavor='raw')
        return 0
        
# VIDEO DRIVER -----------------------------------------------------------------

class VideoDriverImplementation(VideoDriver):
    
    def __init__(self):
        VideoDriver.__init__(self)
        self.map = []
    
    def set_window_size(self):
        self.screen = RSDL.SetVideoMode(self.width, self.height, 32, 0)
        
    def update_display(self):
        RSDL.LockSurface(screen)
        self.draw_pixels()
        RSDL.UnlockSurface(screen)
        RSDL.Flip(screen)
        
    def draw_pixels(self):
        for x in range(self.width):
            for y in range(self.height):
                RSDL_helper.set_pixel(screen, x, y, self.get_pixel_color(x, y))
                
    def get_pixel_color(self, x, y):
        return self.pixels[x+self.width*y]
        #return self.map[self.pixels[x+self.width*y]]
    
    def pixel_to_byte(self, int_number):
        return struct.pack("B", (int_number) & 0xFF, 
                                (int_number >> 8) & 0xFF, 
                                (int_number >> 16) & 0xFF)
        
        
# JOYPAD DRIVER ----------------------------------------------------------------

class JoypadDriverImplementation(JoypadDriver):
    
    def __init__(self):
        JoypadDriver.__init__(self)
        self.last_char = ""
        
    def update(self, event):
        # fetch the event from sdl
        ok = RSDL.WaitEvent(event)
        assert rffi.cast(lltype.Signed, ok) == 1
        type = rffi.getintfield(event, 'c_type')
        if type == RSDL.KEYDOWN:
            self.create_called_key()
            self.on_key_down()
        elif type == RSDL.KEYUP:
            self.create_called_key()
            self.on_key_up()
    
    def create_called_key(self, event):
        p = rffi.cast(RSDL.KeyboardEventPtr, event)
        char = rffi.getintfield(p.c_keysym, 'c_unicode')
        self.last_char = unichr(char).encode('utf-8')
        
        
        
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