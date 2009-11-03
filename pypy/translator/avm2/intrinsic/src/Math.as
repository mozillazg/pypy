package
{
	/// The Math class contains methods and constants that represent common mathematical functions and values.
	public class Math extends Object
	{
		/// A mathematical constant for the base of natural logarithms, expressed as e.
		public static const E : Number;
		/// A mathematical constant for the natural logarithm of 10, expressed as loge10, with an approximate value of 2.302585092994046.
		public static const LN10 : Number;
		/// A mathematical constant for the natural logarithm of 2, expressed as loge2, with an approximate value of 0.6931471805599453.
		public static const LN2 : Number;
		/// A mathematical constant for the base-10 logarithm of the constant e (Math.E), expressed as log10e, with an approximate value of 0.4342944819032518.
		public static const LOG10E : Number;
		/// A mathematical constant for the base-2 logarithm of the constant e, expressed as log2e, with an approximate value of 1.442695040888963387.
		public static const LOG2E : Number;
		/// A mathematical constant for the ratio of the circumference of a circle to its diameter, expressed as pi, with a value of 3.141592653589793.
		public static const PI : Number;
		/// A mathematical constant for the square root of one-half, with an approximate value of 0.7071067811865476.
		public static const SQRT1_2 : Number;
		/// A mathematical constant for the square root of 2, with an approximate value of 1.4142135623730951.
		public static const SQRT2 : Number;

		/// Returns the absolute value of the specified Number.
		public static function abs (x:Number) : Number;

		/// Returns the arc cosine, in radians, of the specified Number.
		public static function acos (x:Number) : Number;

		/// Returns the value, in radians, of the arc sine of the specified Number parameter.
		public static function asin (x:Number) : Number;

		/// Returns the angle, in radians, whose tangent is specified by parameter val.
		public static function atan (x:Number) : Number;

		/// Returns the angle of the point y/x in radians, when measured counterclockwise from a circle's x axis.
		public static function atan2 (y:Number, x:Number) : Number;

		/// Returns the ceiling of the specified number or expression.
		public static function ceil (x:Number) : Number;

		/// Returns the cosine of the specified angle.
		public static function cos (x:Number) : Number;

		/// Returns the value of the base of the natural logarithm (e), to the power of the exponent specified in the parameter val.
		public static function exp (x:Number) : Number;

		/// Returns the floor of the number or expression specified in the parameter val.
		public static function floor (x:Number) : Number;

		/// Returns the natural logarithm of parameter val.
		public static function log (x:Number) : Number;

		public function Math ();

		/// Evaluates parameters val1 and val2 and returns the larger value.
		public static function max (x:Number = null, y:Number = null, ...rest) : Number;

		/// Evaluates parameters val1 and val2 and returns the smaller value.
		public static function min (x:Number = null, y:Number = null, ...rest) : Number;

		/// Returns val1 to the power of val2.
		public static function pow (x:Number, y:Number) : Number;

		/// Returns a pseudo-random number n, where 0 <= n < 1.
		public static function random () : Number;

		/// Returns the value of parameter val rounded up or down to the nearest integer.
		public static function round (x:Number) : Number;

		/// Returns the sine of the specified angle.
		public static function sin (x:Number) : Number;

		/// Returns the square root of the specified number.
		public static function sqrt (x:Number) : Number;

		/// Returns the tangent of the specified angle.
		public static function tan (x:Number) : Number;
	}
}
