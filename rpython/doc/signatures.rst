
Basic types::

  int    - signed machine size integer
  r_uint - unsigned machine size integer
  r_long/r_ulong/r_longlong/r_ulonglong - various integers
  char   - single character (byte)
  bytes  - immutable array of chars
  bytes? - nullable bytes
  float  - double-sized IEEE floating point

Low level types:

  ll.UCHAR
  ll.INT
  ...
  ll.Array(xxx)
  ll.Struct(xxx)
  ll.GcStruct(xxx)
  ll.GcArray(xxx)

Container types::

  list(X)        - resizable list of X
  array(X)       - non-resizable list of X
  dict(X, Y)     - dict of X keys and Y values
  tuple(A, B, C) - tuple of 3 items, A, B, C
  list?(X)       - nullable list, array or dict

Classes::

  class A(object):
      _rpython_ = """
      class foobar.A # <- namespace declaration for type name

      a: int
      b: list(int)
      c: array(int)
      """

PBCs::

  space = rpython_pbc("space.ObjSpace", space) - registers PBC under the name "space.ObjSpace",
                                                 to be used in signatures

Examples of a signature::

  @rpython("int -> int")
  def f(a):
      return a

  @rpython("space.ObjSpace, int, float -> bytes")
  def f(space, i, f):
      return space.str_w(space.newbytes(str(i)))
