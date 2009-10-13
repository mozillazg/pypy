package
{
	/// A RangeError exception is thrown when a numeric value is outside the acceptable range.
	public class RangeError extends Error
	{
		public static const length : int;

		/// Creates a new RangeError object.
		public function RangeError (message:* = "", id:* = 0);
	}
}
