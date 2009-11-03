package
{
	/// The String class is a data type that represents a string of characters.
	public class String extends Object
	{
		/// An integer specifying the number of characters in the specified String object.
		public static const length : int;

		public function get length () : int;

		/// Returns the character in the position specified by the index parameter.
		public function charAt (i:Number = 0) : String;

		/// Returns the numeric Unicode character code of the character at the specified index.
		public function charCodeAt (i:Number = 0) : Number;

		/// Appends the supplied arguments to the end of the String object, converting them to strings if necessary, and returns the resulting string.
		public function concat (...rest) : String;

		/// Returns a string comprising the characters represented by the Unicode character codes in the parameters.
		public static function fromCharCode (...rest) : String;

		/// Searches the string and returns the position of the first occurrence of val found at or after startIndex within the calling string.
		public function indexOf (s:String = undefined, i:Number = 0) : int;

		/// Searches the string from right to left and returns the index of the last occurrence of val found before startIndex.
		public function lastIndexOf (s:String = undefined, i:Number = 2147483647) : int;

		/// Compares the sort order of two or more strings and returns the result of the comparison as an integer.
		public function localeCompare (other:String = null) : int;

		/// Matches the specifed pattern against the string.
		public function match (p:* = null) : Array;

		/// Matches the specifed pattern against the string and returns a new string in which the first match of pattern is replaced with the content specified by repl.
		public function replace (p:* = null, repl:* = null) : String;

		/// Searches for the specifed pattern and returns the index of the first matching substring.
		public function search (p:* = null) : int;

		/// Returns a string that includes the startIndex character and all characters up to, but not including, the endIndex character.
		public function slice (start:Number = 0, end:Number = 2147483647) : String;

		/// Splits a String object into an array of substrings by dividing it wherever the specified delimiter parameter occurs.
		public function split (delim:* = null, limit:* = 4294967295) : Array;

		/// Creates a new String object initialized to the specified string.
		public function String (value:* = "");

		/// Returns a substring consisting of the characters that start at the specified  startIndex and with a length specified by len.
		public function substr (start:Number = 0, len:Number = 2147483647) : String;

		/// Returns a string consisting of the character specified by startIndex and all characters up to endIndex - 1.
		public function substring (start:Number = 0, end:Number = 2147483647) : String;

		/// Returns a copy of this string, with all uppercase characters converted to lowercase.
		public function toLocaleLowerCase () : String;

		/// Returns a copy of this string, with all lowercase characters converted to uppercase.
		public function toLocaleUpperCase () : String;

		/// Returns a copy of this string, with all uppercase characters converted to lowercase.
		public function toLowerCase () : String;

		public function toString () : String;

		/// Returns a copy of this string, with all lowercase characters converted to uppercase.
		public function toUpperCase () : String;

		/// Returns the primitive value of a String instance.
		public function valueOf () : String;
	}
}
