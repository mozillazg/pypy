#ifndef Py_LONGINTREPR_H
#define Py_LONGINTREPR_H

/* 
    Should not be used, but is, by a few projects out there.
*/
#include <stdint.h>


#define PYLONG_BITS_IN_DIGIT  30
typedef uint32_t digit;
typedef int32_t sdigit;
typedef uint64_t twodigits;
typedef int64_t stwodigits;
#define PyLong_SHIFT    30
#define _PyLong_DECIMAL_SHIFT   9 /* max(e such that 10**e fits in a digit) */
#define _PyLong_DECIMAL_BASE    ((digit)1000000000) /* 10 ** DECIMAL_SHIFT */

#define PyLong_BASE ((digit)1 << PyLong_SHIFT)
#define PyLong_MASK ((digit)(PyLong_BASE - 1))

/* b/w compatibility with Python 2.5 */
#define SHIFT   PyLong_SHIFT
#define BASE    PyLong_BASE
#define MASK    PyLong_MASK


#endif
