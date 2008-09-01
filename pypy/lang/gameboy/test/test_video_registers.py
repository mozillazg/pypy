from pypy.lang.gameboy import constants
from pypy.lang.gameboy.video import ControlRegister
from pypy.lang.gameboy.video import StatusRegister
import py


# ControlRegister --------------------------------------------------------------

def test_video_control_reset():
    control = ControlRegister()
    assert control.read() == 0x91
    control.write(0xFF)
    assert control.read() == 0xFF
    control.reset()
    assert control.read() == 0x91
    
    
def test_video_control_read_write_properties():
    control   = ControlRegister()
    properties = ["lcd_enabled",  
                  "window_upper_tile_map_selected", 
                  "window_enabled", 
                  "background_and_window_lower_tile_data_selected",
                  "background_upper_tile_map_selected",
                  "big_sprite_size_selected",
                  "sprite_display_enabled",
                  "background_enabled"]
    properties.reverse()
    for index in range(8):
        property = properties[index];
        control.write(0x00)
        assert control.read() == 0x00
        assert control.__getattribute__(property) == False
        
        control.write(0xFF)
        assert control.read() == 0xFF
        assert control.__getattribute__(property) == True
        
        control.write(0x00)
        control.__setattr__(property, True)
        assert control.__getattribute__(property) == True
        assert control.read() & (1 << index) == (1 << index)
        assert control.read() & (~(1 << index)) == 0
        
        control.write(1 << index)
        assert control.__getattribute__(property) == True
        assert control.read() & (1 << index) == (1 << index)
        assert control.read() & (~(1 << index)) == 0
        
        
# StatusRegister ---------------------------------------------------------------

def test_video_status_reset():
    status = StatusRegister(None)
    assert status.read(extend=True) == 0x02 + 0x80
    
    status.write(0x00, write_all=True)
    assert status.read(extend=True) == 0x00
    status.reset()
    assert status.read(extend=True) == 0x02 + 0x80
    
    status.write(0xFF, write_all=True)
    assert status.read(extend=True) == 0xFF
    status.reset()
    assert status.read(extend=True) == 0x02 + 0x80
    
def test_video_status_mode():
    status = StatusRegister(None)
    assert status.get_mode() == 2
    
    for i in range(3):
        status.set_mode(i)
        assert status.get_mode() == i
    status.set_mode(4)
    assert status.get_mode()  == 0
