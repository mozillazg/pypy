package flash.net
{
	/// The URLVariables class allows you to transfer variables between an application and a server.
	public class URLVariables extends Object
	{
		/// Converts the variable string to properties of the specified URLVariables object.
		public function decode (source:String) : void;

		/// Returns a string containing all enumerable variables, in the MIME content encoding application/x-www-form-urlencoded.
		public function toString () : String;

		/// Creates a new URLVariables object.
		public function URLVariables (source:String = null);
	}
}
