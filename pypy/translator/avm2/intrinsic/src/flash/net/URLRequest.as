package flash.net
{
	/// The URLRequest class captures all of the information in a single HTTP request.
	public class URLRequest extends Object
	{
		/// The MIME content type of the content in the the data property.
		public function get contentType () : String;
		public function set contentType (value:String) : void;

		/// An object containing data to be transmitted with the URL request.
		public function get data () : Object;
		public function set data (value:Object) : void;

		/// A string that uniquely identifies the signed Adobe platform component to be stored to (or retrieved from) the Flash Player cache.
		public function get digest () : String;
		public function set digest (value:String) : void;

		/// Controls the HTTP form submission method.
		public function get method () : String;
		public function set method (value:String) : void;

		/// The array of HTTP request headers to be appended to the HTTP request.
		public function get requestHeaders () : Array;
		public function set requestHeaders (value:Array) : void;

		/// The URL to be requested.
		public function get url () : String;
		public function set url (value:String) : void;

		/// Creates a URLRequest object.
		public function URLRequest (url:String = null);
	}
}
