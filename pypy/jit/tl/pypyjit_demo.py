print "Starting execution..."
try:
    from micronumpy import zeros
    import micronumpy as numpy
    import micronumpy

    from convolve import naive_convolve
    from numpybench import generate_kernel, generate_image

    image = generate_image(128, 128)
    kernel = generate_kernel(5, 5)

    for i in range(100):
        result = naive_convolve(image, kernel)

except Exception, e:
    print "Exception: ", type(e)
    print e
print "Stopping execution..."
