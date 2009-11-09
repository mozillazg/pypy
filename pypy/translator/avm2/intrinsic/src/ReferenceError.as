package
{
	/// A ReferenceError exception is thrown when a reference to an undefined property is attempted on a sealed (nondynamic) object.
	public class ReferenceError extends Error
	{
		public static const length : int;

		/// Creates a new ReferenceError object.
		public function ReferenceError (message:* = "", id:* = 0);
	}
}
