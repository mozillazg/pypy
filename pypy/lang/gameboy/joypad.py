
from pypy.lang.gameboy import constants
from pypy.lang.gameboy.interrupt import Interrupt
from pypy.lang.gameboy.ram import iMemory

class Joypad(iMemory):
    """
    PyGirl GameBoy (TM) Emulator
     
    Joypad Input
    """

    def __init__(self, joypad_driver, interrupt):
        assert isinstance(joypad_driver, JoypadDriver)
        assert isinstance(interrupt, Interrupt)
        self.driver    = joypad_driver
        self.interrupt = interrupt
        self.reset()

    def reset(self):
        self.read_control = 0xF
        self.button_code  = 0xF
        self.cycles       = constants.JOYPAD_CLOCK

    def get_cycles(self):
        return self.cycles

    def emulate(self, ticks):
        self.cycles -= ticks
        if self.cycles <= 0:
            if self.driver.is_raised():
                self.update()
            self.cycles = constants.JOYPAD_CLOCK
            #self.cycles = 150

    def write(self, address, data):
        if address == constants.JOYP:
            self.read_control = (self.read_control & 0xC) + ((data & 0x30)>>4)
            self.update()

    def read(self, address):
        if address == constants.JOYP:
            return (self.read_control << 4) + self.button_code
        return 0xFF

    def update(self):
        old_buttons = self.button_code
        if self.read_control & 0x3 == 1:
            self.button_code = self.driver.get_button_code()
        elif self.read_control & 0x3 == 2:
            self.button_code = self.driver.get_direction_code()
        elif self.read_control & 0x3 == 3:
            self.button_code  = 0xF
        if old_buttons != self.button_code:
            self.interrupt.raise_interrupt(constants.JOYPAD)


# ------------------------------------------------------------------------------


class JoypadDriver(object):
    """
    Maps the Input to the Button and Direction Codes
    """
    def __init__(self):
        self.raised = False
        self.create_buttons()
        self.reset()
        
    def create_buttons(self):
        self.up     = Button(constants.BUTTON_UP)
        self.right  = Button(constants.BUTTON_RIGHT)
        self.down   = Button(constants.BUTTON_DOWN)
        self.left   = Button(constants.BUTTON_LEFT)
        self.start  = Button(constants.BUTTON_START)
        self.select = Button(constants.BUTTON_SELECT)
        self.a      = Button(constants.BUTTON_A)
        self.b      = Button(constants.BUTTON_B)
        self.add_opposite_buttons()
        self.create_button_groups()
        
    def add_opposite_buttons(self):
        self.up.opposite_button    = self.down
        self.down.opposite_button  = self.up
        self.left.opposite_button  = self.right
        self.right.opposite_button = self.left
        
    def create_button_groups(self):
        self.directions = [self.up,    self.right,  self.down, self.left]
        self.buttons    = [self.start, self.select, self.a,    self.b]
        
    def get_buttons(self):
        return self.buttons
    
    def get_directions(self):
        return self.directions
    
    def get_button_code(self):
        code = 0
        for button in self.buttons:
            code |= button.get_code()
        return code
        
    def get_direction_code(self):
        code = 0
        for button in self.directions:
            code |= button.get_code()
        return code
    
    def is_raised(self):
        raised      = self.raised
        self.raised = False
        return raised
    
    def reset(self):
        self.raised = False
        self.release_all_buttons()

    def release_all_buttons(self):
        self.release_buttons()
        self.release_directions()
        
    def release_buttons(self):
        self.up.release()
        self.right.release()
        self.down.release()
        self.left.release()
        
    def release_directions(self):
        self.start.release()
        self.select.release()
        self.a.release()
        self.b.release()
        
    def button_up(self, pressed=True):
        self.up.toggle_button(pressed)
        self.raised = True
    
    def button_right(self, pressed=True):
        self.right.toggle_button(pressed)
        self.raised = True
    
    def button_down(self, pressed=True):
        self.down.toggle_button(pressed)
        self.raised = True
    
    def button_left(self, pressed=True):
        self.left.toggle_button(pressed)
        self.raised = True
    
    def button_start(self, pressed=True):
        self.start.toggle_button(pressed)
        self.raised = True
    
    def button_select(self, pressed=True):
        self.select.toggle_button(pressed)
        self.raised = True
    
    def button_a(self, pressed=True):
        self.a.toggle_button(pressed)
        self.raised = True
    
    def button_b(self, pressed=True):
        self.b.toggle_button(pressed)
        self.raised = True
    
  
# ------------------------------------------------------------------------------  
    
    
class Button(object):
    
    def __init__(self, code_value, opposite_button=None):
        self.code_value      = int(code_value)
        self.opposite_button = opposite_button
        self.pressed         = False
        
    def get_code(self):
        if self.pressed:
            return self.code_value
        else:
            return 0
        
    def toggle_button(self, pressed=True):
        if pressed:
            self.press()
        else:
            self.release()
            
    def release(self):
        self.pressed = False
        
    def press(self):
        if self.opposite_button is not None:
            self.opposite_button.release()
        self.pressed = True
        
    def is_pressed(self):
        return self.pressed