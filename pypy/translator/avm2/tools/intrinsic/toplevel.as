package
{
	/// A special value representing positive Infinity.
	public var Infinity:Number;

	/// A special member of the Number data type that represents a value that is "not a number" (NaN).
	public var NaN:Number;

	/// A special value that applies to untyped variables that have not been initialized or dynamic object properties that are not initialized.
	public var undefined:*;

	/// Displays expressions, or writes to log files, while debugging.
	public function trace (...arguments) : void;

	/// Decodes an encoded URI into a string.
	public function decodeURI (uri:String) : String;

	/// Decodes an encoded URI component into a string.
	public function decodeURIComponent (uri:String) : String;

	/// Encodes a string into a valid URI (Uniform Resource Identifier).
	public function encodeURI (uri:String) : String;

	/// Encodes a string into a valid URI component.
	public function encodeURIComponent (uri:String) : String;

	/// Converts the parameter to a string and encodes it in a URL-encoded format, where most nonalphanumeric characters are replaced with % hexadecimal sequences.
	public function escape (str:String) : String;

	/// Returns true if the value is a finite number, or false if the value is Infinity or -Infinity.
	public function isFinite (num:Number) : Boolean;

	/// Returns true if the value is NaN(not a number).
	public function isNaN (num:Number) : Boolean;

	/// Determines whether the specified string is a valid name for an XML element or attribute.
	public function isXMLName (str:String) : Boolean;

	/// Converts a string to an integer.
	public function parseInt (str:String, radix:uint = 0) : Number;

	/// Converts a string to a floating-point number.
	public function parseFloat (str:String) : Number;

	/// Evaluates the parameter str as a string, decodes the string from URL-encoded format (converting all hexadecimal sequences to ASCII characters), and returns the string.
	public function unescape (str:String) : String;

}

