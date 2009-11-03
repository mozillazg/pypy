package flash.text.engine
{
	import flash.text.engine.TextJustifier;

	/// The TextJustifier class is an abstract base class for the justifier types that you can apply to a TextBlock, specifically the EastAsianJustifier and SpaceJustifier classes.
	public class TextJustifier extends Object
	{
		/// Specifies the line justification for the text in a text block.
		public function get lineJustification () : String;
		public function set lineJustification (value:String) : void;

		/// Specifies the locale to determine the justification rules for the text in a text block.
		public function get locale () : String;

		/// Constructs a cloned copy of the TextJustifier.
		public function clone () : TextJustifier;

		/// Constructs a default TextJustifier subclass appropriate to the specified locale.
		public static function getJustifierForLocale (locale:String) : TextJustifier;

		/// Calling the new TextJustifier() constructor throws an ArgumentError exception.
		public function TextJustifier (locale:String, lineJustification:String);
	}
}
