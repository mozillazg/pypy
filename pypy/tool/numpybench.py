try:
    import numpy as numpy
except ImportError, e:
    import micronumpy as numpy

def generate_image(width, height):
    return numpy.array([[x + y for x in range(width)] for y in range(height)])

def generate_kernel(width, height):
    from math import sin, pi
    #kernel = numpy.zeros((width, height), dtype=int) # FIXME: micronumpy.zeros can't handle missing dtype
    kernel = [[0] * width] * height

    for i in range(width):
        for j in range(height):
            u = i / float(width)
            v = j / float(height)
            kernel[j][i] = int((0.5 + sin(u * pi)) * (0.5 + sin(v * pi))) # DOUBLE FIXME: setitem doesn't coerce to array type
        
    #return kernel
    return numpy.array(kernel)

if __name__ == '__main__':
    from sys import argv as args
    width, height, kwidth, kheight = [int(x) for x in args[1:]]

    image = generate_image(width, height)
    kernel = generate_kernel(kwidth, kheight)

    from timeit import Timer
    convolve_timer = Timer('naive_convolve(image, kernel)', 'from convolve import naive_convolve; from __main__ import image, kernel; gc.enable()')
    count = 100
    print "%.5f sec/pass" % (convolve_timer.timeit(number=count)/count)
