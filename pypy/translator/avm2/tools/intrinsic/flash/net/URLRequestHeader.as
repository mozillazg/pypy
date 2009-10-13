package flash.net
{
	/// A URLRequestHeader object encapsulates a single HTTP request header and consists of a name/value pair.
	public class URLRequestHeader extends Object
	{
		/// An HTTP request header name (such as Content-Type or SOAPAction).
		public var name : String;
		/// The value associated with the name property (such as text/plain).
		public var value : String;

		/// Creates a new URLRequestHeader object that encapsulates a single HTTP request header.
		public function URLRequestHeader (name:String = "", value:String = "");
	}
}
