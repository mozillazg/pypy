
import pyglet
pyglet.options['audio'] = ('openal', 'silent')
        
from pyglet        import window
from pyglet.window import key
from pyglet        import media

from pypy.lang.gameboy.joypad import JoypadDriver
from pypy.lang.gameboy.video  import VideoDriver
from pypy.lang.gameboy.sound  import SoundDriver


# GAMEBOY ----------------------------------------------------------------------

class GameBoyImplementation(GameBoy):
    
    def __init__(self):
        self.iniWindow()
        GameBoy.__init__(self)
        
    def iniWindow(self):
        self.win = window.Window()
        
    def createDrivers(self):
        self.clock = Clock()
        self.joypadDriver = JoypadDriverImplementation(self.win)
        self.videoDriver  = VideoDriverImplementation(self.win)
        self.soundDriver  = SoundDriverImplementation(self.win)
        

# JOYPAD DRIVER ----------------------------------------------------------------

class JoypadDriverImplementation(object):
    
    def __ini__(self, win):
        JoypadDriver.__ini__(self)
        self.crateButtonKeyCodes()
        self.win = win
        self.createListeners()
        
    def crateButtonKeyCodes(self):
        self.buttonKeyCodes = {key.UP    : (self.buttonUp),
                              key.RIGHT : (self.buttonRight), 
                              key.DOWN  : (self.buttonDown), 
                              key.LEFT  : (self.buttonLeft), 
                              key.ENTER : (self.buttonStart),
                              key.SPACE : (self.buttonSelect),
                              key.A     : (self.buttonA), 
                              key.B     : (self.ButtonB)}
        
    def createListeners(self):
        self.win.on_key_press = self.on_key_press
        self.win.on_key_release = self.on_key_press
        
    def on_key_press(symbol, modifiers): 
        pressButtonFunction = self.getButton(symbol, modifiers)
        if pressButtonFunction != None:
            pressButtonFunction(True)
    
    def on_key_release(symbol, modifiers): 
        pressButtonFunction = self.getButton(symbol, modifiers)
        if pressButtonFunction != None:
            pressButtonFunction(False)
            
    def getButton(self, symbol, modifiers):
        if symbol in self.buttonKeyCodes:
            if len(self.buttonKeyCodes[symbol]) == 1 or\
                    self.buttonKeyCodes[symbol][1] ==  modifiers:
                return self.buttonKeyCodes[symbol][0]
        return None
        
        
# SOUND DRIVER -----------------------------------------------------------------

class SoundDriverImplementation(SoundDriver):
    
    def __init__(self):
        SoundDriver.__init__(self)
        self.createSoundDriver()
        self.enabled = True
        self.sampleRate = 44100
        self.channelCount = 2
        self.bitsPerSample = 8

    def createSoundDriver(self):
        
    def start(self):
        pass
        
    def stop(self):
        pass
    
    def write(self, buffer, length):
        pass
    
    
# VIDEO DRIVER -----------------------------------------------------------------

class VideoDriverImplementation(VideoDriver):
    
    def __init__(self, win):
        VideoDriver.__init__(self)
        self.win = win
        self.win.on_resize = self.on_resize
        self.setWindowSize()
        self.createImageBuffer()

    def createImageBuffer(self):
        self.buffers = image.get_buffer_manager()
        self.imageBuffer = self.buffers.get_color_buffer()
        
    def on_resize(self, width, height):
        pass
    
    def setWindowSize(self):
        self.win.setSize(self.width, self.height)
        
    def updateDisplay(self):
        self.clearPixels()
        
        
# ==============================================================================

if __name__ == '__main__':
    print "starting gameboy"
    gameboy = GameBoyImplementation()
