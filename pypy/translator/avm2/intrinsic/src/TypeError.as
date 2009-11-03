package
{
	/// A TypeError exception is thrown when the actual type of an operand is different from the expected type.
	public class TypeError extends Error
	{
		public static const length : int;

		/// Creates a new TypeError object.
		public function TypeError (message:* = "", id:* = 0);
	}
}
