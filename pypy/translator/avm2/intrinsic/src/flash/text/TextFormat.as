package flash.text
{
	/// The TextFormat class represents character formatting information.
	public class TextFormat extends Object
	{
		/// Indicates the alignment of the paragraph.
		public function get align () : String;
		public function set align (value:String) : void;

		/// Indicates the block indentation in pixels.
		public function get blockIndent () : Object;
		public function set blockIndent (value:Object) : void;

		/// Specifies whether the text is boldface.
		public function get bold () : Object;
		public function set bold (value:Object) : void;

		/// Indicates that the text is part of a bulleted list.
		public function get bullet () : Object;
		public function set bullet (value:Object) : void;

		/// Indicates the color of the text.
		public function get color () : Object;
		public function set color (value:Object) : void;

		public function get display () : String;
		public function set display (value:String) : void;

		/// The name of the font for text in this text format, as a string.
		public function get font () : String;
		public function set font (value:String) : void;

		/// Indicates the indentation from the left margin to the first character in the paragraph.
		public function get indent () : Object;
		public function set indent (value:Object) : void;

		/// Indicates whether text in this text format is italicized.
		public function get italic () : Object;
		public function set italic (value:Object) : void;

		/// A Boolean value that indicates whether kerning is enabled (true) or disabled (false).
		public function get kerning () : Object;
		public function set kerning (value:Object) : void;

		/// An integer representing the amount of vertical space (called leading) between lines.
		public function get leading () : Object;
		public function set leading (value:Object) : void;

		/// The left margin of the paragraph, in pixels.
		public function get leftMargin () : Object;
		public function set leftMargin (value:Object) : void;

		/// A number representing the amount of space that is uniformly distributed between all characters.
		public function get letterSpacing () : Object;
		public function set letterSpacing (value:Object) : void;

		/// The right margin of the paragraph, in pixels.
		public function get rightMargin () : Object;
		public function set rightMargin (value:Object) : void;

		/// The point size of text in this text format.
		public function get size () : Object;
		public function set size (value:Object) : void;

		/// Specifies custom tab stops as an array of non-negative integers.
		public function get tabStops () : Array;
		public function set tabStops (value:Array) : void;

		/// Indicates the target window where the hyperlink is displayed.
		public function get target () : String;
		public function set target (value:String) : void;

		/// Indicates whether the text that uses this text format is underlined (true) or not (false).
		public function get underline () : Object;
		public function set underline (value:Object) : void;

		/// Indicates the target URL for the text in this text format.
		public function get url () : String;
		public function set url (value:String) : void;

		/// Creates a TextFormat object with the specified properties.
		public function TextFormat (font:String = null, size:Object = null, color:Object = null, bold:Object = null, italic:Object = null, underline:Object = null, url:String = null, target:String = null, align:String = null, leftMargin:Object = null, rightMargin:Object = null, indent:Object = null, leading:Object = null);
	}
}
