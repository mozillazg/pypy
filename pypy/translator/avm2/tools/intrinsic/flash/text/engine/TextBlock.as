package flash.text.engine
{
	import flash.text.engine.TextJustifier;
	import flash.text.engine.TextLine;
	import flash.text.engine.ContentElement;
	import flash.text.engine.FontDescription;
	import flash.text.engine.TabStop;

	/// The TextBlock class is a factory for the creation of TextLine objects, which you can render by placing them on the display list.
	public class TextBlock extends Object
	{
		/// Provides a way for the author to associate arbitrary data with the text block.
		public var userData : *;

		/// Specifies that you want to enhance screen appearance at the expense of what-you-see-is-what-you-get (WYSIWYG) print fidelity.
		public function get applyNonLinearFontScaling () : Boolean;
		public function set applyNonLinearFontScaling (value:Boolean) : void;

		/// The font used to determine the baselines for all the lines created from the block, independent of their content.
		public function get baselineFontDescription () : FontDescription;
		public function set baselineFontDescription (value:FontDescription) : void;

		/// The font size used to calculate the baselines for the lines created from the block.
		public function get baselineFontSize () : Number;
		public function set baselineFontSize (value:Number) : void;

		/// Specifies which baseline is at y=0 for lines created from this block.
		public function get baselineZero () : String;
		public function set baselineZero (value:String) : void;

		/// Specifies the default bidirectional embedding level of the text in the text block.
		public function get bidiLevel () : int;
		public function set bidiLevel (value:int) : void;

		/// Holds the contents of the text block.
		public function get content () : ContentElement;
		public function set content (value:ContentElement) : void;

		/// Identifies the first line in the text block in which TextLine.validity is not equal to TextLineValidity.VALID.
		public function get firstInvalidLine () : TextLine;

		/// The first TextLine in the TextBlock, if any.
		public function get firstLine () : TextLine;

		/// The last TextLine in the TextBlock, if any.
		public function get lastLine () : TextLine;

		/// Rotates the text lines in the text block as a unit.
		public function get lineRotation () : String;
		public function set lineRotation (value:String) : void;

		/// Specifies the tab stops for the text in the text block, in the form of a Vector of TabStop objects.
		public function get tabStops () : Vector.<TabStop>;
		public function set tabStops (value:Vector.<TabStop>) : void;

		/// Specifies the TextJustifier to use during line creation.
		public function get textJustifier () : TextJustifier;
		public function set textJustifier (value:TextJustifier) : void;

		/// Indicates the result of a createTextLine() operation.
		public function get textLineCreationResult () : String;

		/// Instructs the text block to create a line of text from its content, beginning at the point specified by the previousLine parameter and breaking at the point specified by the width parameter.
		public function createTextLine (previousLine:TextLine = null, width:Number = 1000000, lineOffset:Number = 0, fitSomething:Boolean = false) : TextLine;

		/// Dumps the underlying contents of the TextBlock as an XML string.
		public function dump () : String;

		/// Finds the index of the next Atom boundary from the specified character index, not including the character at the specified index.
		public function findNextAtomBoundary (afterCharIndex:int) : int;

		/// Finds the index of the next word boundary from the specified character index, not including the character at the specified index.
		public function findNextWordBoundary (afterCharIndex:int) : int;

		/// Finds the index of the previous atom boundary to the specified character index, not including the character at the specified index.
		public function findPreviousAtomBoundary (beforeCharIndex:int) : int;

		/// Finds the index of the previous word boundary to the specified character index, not including the character at the specified index.
		public function findPreviousWordBoundary (beforeCharIndex:int) : int;

		/// Returns the TextLine containing the character specified by the charIndex parameter.
		public function getTextLineAtCharIndex (charIndex:int) : TextLine;

		/// Removes a range of text lines from the list of lines maintained by the TextBlock.
		public function releaseLines (firstLine:TextLine, lastLine:TextLine) : void;

		/// Creates a TextBlock object
		public function TextBlock (content:ContentElement = null, tabStops:Vector.<TabStop> = null, textJustifier:TextJustifier = null, lineRotation:String = "rotate0", baselineZero:String = "roman", bidiLevel:int = 0, applyNonLinearFontScaling:Boolean = true, baselineFontDescription:FontDescription = null, baselineFontSize:Number = 12);
	}
}
