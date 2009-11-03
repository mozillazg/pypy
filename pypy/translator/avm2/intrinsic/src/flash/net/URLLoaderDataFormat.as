package flash.net
{
	/// The URLLoaderDataFormat class provides values that specify how downloaded data is received.
	public class URLLoaderDataFormat extends Object
	{
		/// Specifies that downloaded data is received as raw binary data.
		public static const BINARY : String;
		/// Specifies that downloaded data is received as text.
		public static const TEXT : String;
		/// Specifies that downloaded data is received as URL-encoded variables.
		public static const VARIABLES : String;

		public function URLLoaderDataFormat ();
	}
}
