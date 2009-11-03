package
{
	/// The RegExp class lets you work with regular expressions, which are patterns that you can use to perform searches in strings and to replace text in strings.
	public class RegExp extends Object
	{
		public static const length : int;

		/// Specifies whether the dot character (.) in a regular expression pattern matches new-line characters.
		public function get dotall () : Boolean;

		/// Specifies whether to use extended mode for the regular expression.
		public function get extended () : Boolean;

		/// Specifies whether to use global matching for the regular expression.
		public function get global () : Boolean;

		/// Specifies whether the regular expression ignores case sensitivity.
		public function get ignoreCase () : Boolean;

		/// Specifies the index position in the string at which to start the next search.
		public function get lastIndex () : int;
		public function set lastIndex (i:int) : void;

		/// Specifies whether the m (multiline) flag is set.
		public function get multiline () : Boolean;

		/// Specifies the pattern portion of the regular expression.
		public function get source () : String;

		/// Performs a search for the regular expression on the given string str.
		public function exec (s:String = "") : *;

		/// Lets you construct a regular expression from two strings.
		public function RegExp (pattern:* = null, options:* = null);

		/// Tests for the match of the regular expression in the given string str.
		public function test (s:String = "") : Boolean;
	}
}
