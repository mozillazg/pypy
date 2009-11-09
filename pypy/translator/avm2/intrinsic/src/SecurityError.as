package
{
	/// The SecurityError exception is thrown when some type of security violation takes place.
	public class SecurityError extends Error
	{
		public static const length : int;

		/// Creates a new SecurityError object.
		public function SecurityError (message:* = "", id:* = 0);
	}
}
