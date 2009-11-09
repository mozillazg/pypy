package
{
	/// A URIError exception is thrown when one of the global URI handling functions is used in a way that is incompatible with its definition.
	public class URIError extends Error
	{
		public static const length : int;

		/// Creates a new URIError object.
		public function URIError (message:* = "", id:* = 0);
	}
}
