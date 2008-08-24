from pypy.lang.gameboy import constants
from pypy.lang.gameboy.video import VideoControl
import py

def test_video_control_reset():
    control = VideoControl()
    assert control.read() == 0x91
    control.write(0xFF)
    assert control.read() == 0xFF
    control.reset()
    assert control.read() == 0x91
    
    
def test_read_write_properties():
    control   = VideoControl()
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
        
