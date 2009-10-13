package
{
	/// The uint class provides methods for working with a data type representing a 32-bit unsigned integer.
	public class uint extends Object
	{
		public static const length : int;
		/// The largest representable 32-bit unsigned integer, which is 4,294,967,295.
		public static const MAX_VALUE : uint;
		/// The smallest representable unsigned integer, which is 0.
		public static const MIN_VALUE : uint;

		/// Returns a string representation of the number in exponential notation.
		public function toExponential (p:* = 0) : String;

		/// Returns a string representation of the number in fixed-point notation.
		public function toFixed (p:* = 0) : String;

		/// Returns a string representation of the number either in exponential notation or in fixed-point notation.
		public function toPrecision (p:* = 0) : String;

		/// Returns the string representation of a uint object.
		public function toString (radix:* = 10) : String;

		/// Creates a new uint object.
		public function uint (value:* = 0);

		/// Returns the primitive uint type value of the specified uint object.
		public function valueOf () : uint;
	}
}
