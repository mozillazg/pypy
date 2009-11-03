package flash.text
{
	import flash.display.InteractiveObject;
	import flash.text.TextFormat;
	import flash.display.DisplayObject;
	import flash.geom.Rectangle;
	import flash.text.StyleSheet;
	import flash.text.TextLineMetrics;

	/**
	 * Flash Player dispatches the textInput event when a user enters one or more characters of text.
	 * @eventType flash.events.TextEvent.TEXT_INPUT
	 */
	[Event(name="textInput", type="flash.events.TextEvent")] 

	/**
	 * Dispatched by a TextField object after the user scrolls.
	 * @eventType flash.events.Event.SCROLL
	 */
	[Event(name="scroll", type="flash.events.Event")] 

	/**
	 * Dispatched when a user clicks a hyperlink in an HTML-enabled text field, where the URL begins with "event:".
	 * @eventType flash.events.TextEvent.LINK
	 */
	[Event(name="link", type="flash.events.TextEvent")] 

	/**
	 * Dispatched after a control value is modified, unlike the textInput event, which is dispatched before the value is modified.
	 * @eventType flash.events.Event.CHANGE
	 */
	[Event(name="change", type="flash.events.Event")] 

	/// The TextField class is used to create display objects for text display and input.
	public class TextField extends InteractiveObject
	{
		/// When set to true and the text field is not in focus, Flash Player highlights the selection in the text field in gray.
		public function get alwaysShowSelection () : Boolean;
		public function set alwaysShowSelection (value:Boolean) : void;

		/// The type of anti-aliasing used for this text field.
		public function get antiAliasType () : String;
		public function set antiAliasType (antiAliasType:String) : void;

		/// Controls automatic sizing and alignment of text fields.
		public function get autoSize () : String;
		public function set autoSize (value:String) : void;

		/// Specifies whether the text field has a background fill.
		public function get background () : Boolean;
		public function set background (value:Boolean) : void;

		/// The color of the text field background.
		public function get backgroundColor () : uint;
		public function set backgroundColor (value:uint) : void;

		/// Specifies whether the text field has a border.
		public function get border () : Boolean;
		public function set border (value:Boolean) : void;

		/// The color of the text field border.
		public function get borderColor () : uint;
		public function set borderColor (value:uint) : void;

		/// An integer (1-based index) that indicates the bottommost line that is currently visible in the specified text field.
		public function get bottomScrollV () : int;

		/// The index of the insertion point (caret) position.
		public function get caretIndex () : int;

		/// A Boolean value that specifies whether extra white space (spaces, line breaks, and so on) in a text field with HTML text is removed.
		public function get condenseWhite () : Boolean;
		public function set condenseWhite (value:Boolean) : void;

		/// Specifies the format applied to newly inserted text, such as text inserted with the replaceSelectedText() method or text entered by a user.
		public function get defaultTextFormat () : TextFormat;
		public function set defaultTextFormat (format:TextFormat) : void;

		/// Specifies whether the text field is a password text field.
		public function get displayAsPassword () : Boolean;
		public function set displayAsPassword (value:Boolean) : void;

		/// Specifies whether to render by using embedded font outlines.
		public function get embedFonts () : Boolean;
		public function set embedFonts (value:Boolean) : void;

		/// The type of grid fitting used for this text field.
		public function get gridFitType () : String;
		public function set gridFitType (gridFitType:String) : void;

		/// Contains the HTML representation of the text field contents.
		public function get htmlText () : String;
		public function set htmlText (value:String) : void;

		/// The number of characters in a text field.
		public function get length () : int;

		/// The maximum number of characters that the text field can contain, as entered by a user.
		public function get maxChars () : int;
		public function set maxChars (value:int) : void;

		/// The maximum value of scrollH.
		public function get maxScrollH () : int;

		/// The maximum value of scrollV.
		public function get maxScrollV () : int;

		/// A Boolean value that indicates whether Flash Player automatically scrolls multiline text fields when the user clicks a text field and rolls the mouse wheel.
		public function get mouseWheelEnabled () : Boolean;
		public function set mouseWheelEnabled (value:Boolean) : void;

		/// Indicates whether field is a multiline text field.
		public function get multiline () : Boolean;
		public function set multiline (value:Boolean) : void;

		/// Defines the number of text lines in a multiline text field.
		public function get numLines () : int;

		/// Indicates the set of characters that a user can enter into the text field.
		public function get restrict () : String;
		public function set restrict (value:String) : void;

		/// The current horizontal scrolling position.
		public function get scrollH () : int;
		public function set scrollH (value:int) : void;

		/// The vertical position of text in a text field.
		public function get scrollV () : int;
		public function set scrollV (value:int) : void;

		/// A Boolean value that indicates whether the text field is selectable.
		public function get selectable () : Boolean;
		public function set selectable (value:Boolean) : void;

		public function get selectedText () : String;

		/// The zero-based character index value of the first character in the current selection.
		public function get selectionBeginIndex () : int;

		/// The zero-based character index value of the last character in the current selection.
		public function get selectionEndIndex () : int;

		/// The sharpness of the glyph edges in this text field.
		public function get sharpness () : Number;
		public function set sharpness (value:Number) : void;

		/// Attaches a style sheet to the text field.
		public function get styleSheet () : StyleSheet;
		public function set styleSheet (value:StyleSheet) : void;

		/// A string that is the current text in the text field.
		public function get text () : String;
		public function set text (value:String) : void;

		/// The color of the text in a text field, in hexadecimal format.
		public function get textColor () : uint;
		public function set textColor (value:uint) : void;

		/// The height of the text in pixels.
		public function get textHeight () : Number;

		/// The width of the text in pixels.
		public function get textWidth () : Number;

		/// The thickness of the glyph edges in this text field.
		public function get thickness () : Number;
		public function set thickness (value:Number) : void;

		/// The type of the text field.
		public function get type () : String;
		public function set type (value:String) : void;

		/// Specifies whether to copy and paste the text formatting along with the text.
		public function get useRichTextClipboard () : Boolean;
		public function set useRichTextClipboard (value:Boolean) : void;

		/// A Boolean value that indicates whether the text field has word wrap.
		public function get wordWrap () : Boolean;
		public function set wordWrap (value:Boolean) : void;

		/// Appends text to the end of the existing text of the TextField.
		public function appendText (newText:String) : void;

		/// Returns a rectangle that is the bounding box of the character.
		public function getCharBoundaries (charIndex:int) : Rectangle;

		/// Returns the zero-based index value of the character.
		public function getCharIndexAtPoint (x:Number, y:Number) : int;

		/// The zero-based index value of the character.
		public function getFirstCharInParagraph (charIndex:int) : int;

		/// Returns a DisplayObject reference for the given id, for an image or SWF file that has been added to an HTML-formatted text field by using an <img> tag.
		public function getImageReference (id:String) : DisplayObject;

		/// The zero-based index value of the line at a specified point.
		public function getLineIndexAtPoint (x:Number, y:Number) : int;

		/// The zero-based index value of the line containing the character that the the charIndex parameter specifies.
		public function getLineIndexOfChar (charIndex:int) : int;

		/// Returns the number of characters in a specific text line.
		public function getLineLength (lineIndex:int) : int;

		/// Returns metrics information about a given text line.
		public function getLineMetrics (lineIndex:int) : TextLineMetrics;

		/// The zero-based index value of the first character in the line.
		public function getLineOffset (lineIndex:int) : int;

		/// The text string contained in the specified line.
		public function getLineText (lineIndex:int) : String;

		/// The zero-based index value of the character.
		public function getParagraphLength (charIndex:int) : int;

		public function getRawText () : String;

		/// Returns a TextFormat object.
		public function getTextFormat (beginIndex:int = -1, endIndex:int = -1) : TextFormat;

		public function getTextRuns (beginIndex:int = 0, endIndex:int = 2147483647) : Array;

		public function getXMLText (beginIndex:int = 0, endIndex:int = 2147483647) : String;

		public function insertXMLText (beginIndex:int, endIndex:int, richText:String, pasting:Boolean = false) : void;

		/// Returns true if an embedded font is available with the specified fontName and fontStyle where Font.fontType is flash.text.FontType.EMBEDDED.
		public static function isFontCompatible (fontName:String, fontStyle:String) : Boolean;

		/// Replaces the current selection with the contents of the value parameter.
		public function replaceSelectedText (value:String) : void;

		/// Replaces a range of characters.
		public function replaceText (beginIndex:int, endIndex:int, newText:String) : void;

		/// Sets a new text selection.
		public function setSelection (beginIndex:int, endIndex:int) : void;

		/// Applies text formatting.
		public function setTextFormat (format:TextFormat, beginIndex:int = -1, endIndex:int = -1) : void;

		/// Creates a new TextField instance.
		public function TextField ();
	}
}
