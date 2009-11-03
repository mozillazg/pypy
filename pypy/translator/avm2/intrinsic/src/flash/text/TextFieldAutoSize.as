package flash.text
{
	/// The TextFieldAutoSize class is an enumeration of constant values used in setting the autoSize property of the TextField class.
	public class TextFieldAutoSize extends Object
	{
		/// Specifies that the text is to be treated as center-justified text.
		public static const CENTER : String;
		/// Specifies that the text is to be treated as left-justified text, meaning that the left side of the text field remains fixed and any resizing of a single line is on the right side.
		public static const LEFT : String;
		/// Specifies that no resizing is to occur.
		public static const NONE : String;
		/// Specifies that the text is to be treated as right-justified text, meaning that the right side of the text field remains fixed and any resizing of a single line is on the left side.
		public static const RIGHT : String;

		public function TextFieldAutoSize ();
	}
}
