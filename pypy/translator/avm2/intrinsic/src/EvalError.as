package
{
	/// The EvalError class represents an error that occurs when user code calls the eval() function or attempts to use the new operator with the Function object.
	public class EvalError extends Error
	{
		public static const length : int;

		/// Creates a new EvalError object.
		public function EvalError (message:* = "", id:* = 0);
	}
}
