try:
    import numpy as numpy
except ImportError, e:
    import micronumpy as numpy

def generate_image(width, height, dtype=float):
    return numpy.array([[x + y for x in range(width)] for y in range(height)], dtype=dtype)

def generate_kernel(width, height, dtype=float):
    from math import sin, pi
    kernel = numpy.zeros((width, height), dtype=dtype) # FIXME: micronumpy.zeros can't handle missing dtype

    for i in range(width):
        for j in range(height):
            u = (i + 0.5) / float(width)
            v = (j + 0.5) / float(height)
            kernel[j,i] = int((0.5 + sin(u * pi)) * (0.5 + sin(v * pi))) # DOUBLE FIXME: setitem doesn't coerce to array type
            print "kernel[%d,%d] = %s" % (j, i, kernel[j][i])
        
    print kernel
    return kernel

if __name__ == '__main__':
    from optparse import OptionParser

    option_parser = OptionParser()
    option_parser.add_option('--kernel-size', dest='kernel', default='3x3',
                             help="The size of the convolution kernel, given as WxH. ie 3x3"
                                  "Note that both dimensions must be odd.")
    option_parser.add_option('--image-size', dest='image', default='256x256',
                             help="The size of the image, given as WxH. ie. 256x256")
    option_parser.add_option('--runs', '--count', dest='count', default=1000,
                             help="The number of times to run the convolution filter")

    options, args = option_parser.parse_args()
    
    def parse_dimension(arg):
        return [int(s.strip()) for s in arg.split('x')]

    width, height = parse_dimension(options.image)
    kwidth, kheight = parse_dimension(options.kernel)
    count = int(options.count)

    dtype = float
    image = generate_image(width, height, dtype)
    kernel = generate_kernel(kwidth, kheight, dtype)

    print "Timing"
    from timeit import Timer
    convolve_timer = Timer('naive_convolve(image, kernel)', 'from convolve import naive_convolve; from __main__ import image, kernel; gc.enable()')
    print "%.5f sec/pass" % (convolve_timer.timeit(number=count)/count)
