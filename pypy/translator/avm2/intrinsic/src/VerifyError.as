package
{
	/// The VerifyError class represents an error that occurs when a malformed or corrupted SWF file is encountered.
	public class VerifyError extends Error
	{
		public static const length : int;

		/// Creates a new VerifyError object.
		public function VerifyError (message:* = "", id:* = 0);
	}
}
