package
{
	/// A data type representing an IEEE-754 double-precision floating-point number.
	public class Number extends Object
	{
		public static const length : int;
		/// The largest representable number (double-precision IEEE-754).
		public static const MAX_VALUE : Number;
		/// The smallest representable non-negative, non-zero, number (double-precision IEEE-754).
		public static const MIN_VALUE : Number;
		/// The IEEE-754 value representing Not a Number (NaN).
		public static const NaN : Number;
		/// Specifies the IEEE-754 value representing negative infinity.
		public static const NEGATIVE_INFINITY : Number;
		/// Specifies the IEEE-754 value representing positive infinity.
		public static const POSITIVE_INFINITY : Number;

		/// Creates a Number with the specified value.
		public function Number (value:* = 0);

		/// Returns a string representation of the number in exponential notation.
		public function toExponential (p:* = 0) : String;

		/// Returns a string representation of the number in fixed-point notation.
		public function toFixed (p:* = 0) : String;

		/// Returns a string representation of the number either in exponential notation or in fixed-point notation.
		public function toPrecision (p:* = 0) : String;

		/// Returns the string representation of this Number using the specified radix parameter as the numeric base.
		public function toString (radix:* = 10) : String;

		/// Returns the primitive value type of the specified Number object.
		public function valueOf () : Number;
	}
}
