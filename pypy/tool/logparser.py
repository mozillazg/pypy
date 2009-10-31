#! /usr/bin/env python
"""
Syntax:
    python logparser.py <action> <logfilename> <options...>

Actions:
    draw-time   draw a timeline image of the log (format PPM)
"""
import autopath
import sys, re
from pypy.rlib.debug import DebugLog


def parse_log_file(filename):
    r_start = re.compile(r"\[([0-9a-f]+)\] \{([\w-]+)$")
    r_stop  = re.compile(r"\[([0-9a-f]+)\] ([\w-]+)\}$")
    log = DebugLog()
    f = open(filename, 'r')
    for line in f:
        line = line.rstrip()
        match = r_start.match(line)
        if match:
            log.debug_start(match.group(2), time=int(match.group(1), 16))
            continue
        match = r_stop.match(line)
        if match:
            log.debug_stop(match.group(2), time=int(match.group(1), 16))
            continue
        log.debug_print(line)
    f.close()
    return log

def getsubcategories(log):
    return [entry for entry in log if entry[0] != 'debug_print']

# ____________________________________________________________


COLORS = {
    '': (160, 160, 160),
    'gc-': (192, 0, 64),
    'gc-minor': (192, 0, 16),
    'gc-collect': (255, 0, 0),
    }

def getcolor(category):
    while category not in COLORS:
        category = category[:-1]
    return COLORS[category]

def getlightercolor((r, g, b)):
    return ((r*2+255)//3, (g*2+255)//3, (b*2+255)//3)

def getdarkercolor((r, g, b)):
    return (r*2//3, g*2//3, b*2//3)

def getlabel(text, _cache={}):
    try:
        return _cache[text]
    except KeyError:
        pass
    from PIL import Image, ImageDraw
    if None not in _cache:
        image = Image.new("RGBA", (1, 1), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        _cache[None] = draw
    else:
        draw = _cache[None]
    sx, sy = draw.textsize(text)
    texthoriz = Image.new("RGBA", (sx, sy), (0, 0, 0, 0))
    ImageDraw.Draw(texthoriz).text((0, 0), text, fill=(0, 0, 0))
    textvert = texthoriz.rotate(90)
    _cache[text] = sx, sy, texthoriz, textvert
    return _cache[text]


def get_timeline_image(log, width=900, height=150):
    from PIL import Image, ImageDraw
    width = int(width)
    height = int(height)
    maincats = getsubcategories(log)
    timestart0 = maincats[0][1]
    timestop0  = maincats[-1][2]
    assert timestop0 > timestart0
    timefactor = float(width) / (timestop0 - timestart0)
    #
    def recdraw(sublist, subheight):
        firstx1 = None
        for category1, timestart1, timestop1, subcats in sublist:
            x1 = int((timestart1 - timestart0) * timefactor)
            x2 = int((timestop1 - timestart0) * timefactor)
            y1 = (height - subheight) / 2
            y2 = y1 + subheight
            color = getcolor(category1)
            if firstx1 is None:
                firstx1 = x1
            if x2 <= x1 + 1:
                x2 = x1 + 1   # not wide enough: don't show start and end lines
            else:
                draw.line([x1, y1+1, x1, y2-1], fill=getlightercolor(color))
                x1 += 1
                x2 -= 1
                draw.line([x2, y1+1, x2, y2-1], fill=getdarkercolor(color))
            draw.line([x1, y1, x2-1, y1], fill=getlightercolor(color))
            y1 += 1
            y2 -= 1
            draw.line([x1, y2, x2-1, y2], fill=getdarkercolor(color))
            draw.rectangle([x1, y1, x2-1, y2-1], fill=color)
            if subcats:
                x2 = recdraw(subcats, subheight * 0.94) - 1
            sx, sy, texthoriz, textvert = getlabel(category1)
            if sx <= x2-x1-8:
                image.paste(texthoriz, (x1+5, y1+5), texthoriz)
            elif sy <= x2-x1-2:
                image.paste(textvert, (x1+1, y1+5), textvert)
        return firstx1
    #
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    recdraw(maincats, height)
    return image

def draw_timeline_image(log, output=None, **kwds):
    image = get_timeline_image(log, **kwds)
    if output is None:
        image.save(sys.stdout, 'png')
    else:
        image.save(output)

# ____________________________________________________________


ACTIONS = {
    'draw-time': (draw_timeline_image, ['width=', 'height=', 'output=']),
    }

if __name__ == '__main__':
    import getopt
    if len(sys.argv) < 2:
        print __doc__
        sys.exit(2)
    action = sys.argv[1]
    func, longopts = ACTIONS[action]
    options, args = getopt.gnu_getopt(sys.argv[2:], '', longopts)
    if len(args) != 1:
        print __doc__
        sys.exit(2)

    kwds = {}
    for name, value in options:
        assert name.startswith('--')
        kwds[name[2:]] = value
    log = parse_log_file(args[0])
    func(log, **kwds)
