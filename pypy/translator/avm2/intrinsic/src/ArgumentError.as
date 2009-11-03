package
{
	/// The ArgumentError class represents an error that occurs when the arguments supplied in a function do not match the arguments defined for that function.
	public class ArgumentError extends Error
	{
		public static const length : int;

		/// Creates an ArgumentError object.
		public function ArgumentError (message:* = "", id:* = 0);
	}
}
