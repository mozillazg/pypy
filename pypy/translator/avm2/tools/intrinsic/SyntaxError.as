package
{
	/// A SyntaxError exception is thrown when a parsing error occurs, for one of the following reasons:.
	public class SyntaxError extends Error
	{
		public static const length : int;

		/// Creates a new SyntaxError object.
		public function SyntaxError (message:* = "", id:* = 0);
	}
}
