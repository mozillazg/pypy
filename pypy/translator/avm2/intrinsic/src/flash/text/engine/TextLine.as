package flash.text.engine
{
	import flash.display.DisplayObjectContainer;
	import flash.text.engine.TextLineMirrorRegion;
	import flash.display.DisplayObject;
	import flash.text.engine.TextLine;
	import flash.events.EventDispatcher;
	import flash.ui.ContextMenu;
	import flash.text.engine.TextBlock;
	import flash.geom.Rectangle;

	/// The TextLine class is used to display text on the display list.
	public class TextLine extends DisplayObjectContainer
	{
		/// The maximum requested width of a text line, in pixels.
		public static const MAX_LINE_WIDTH : int;
		/// Provides a way for the author to associate arbitrary data with the text line.
		public var userData : *;

		/// Specifies the number of pixels from the baseline to the top of the tallest characters in the line.
		public function get ascent () : Number;

		/// The number of atoms in the line, which is the number of indivisible elements, including spaces and graphic elements.
		public function get atomCount () : int;

		public function set contextMenu (cm:ContextMenu) : void;

		/// Specifies the number of pixels from the baseline to the bottom of the lowest-descending characters in the line.
		public function get descent () : Number;

		public function set focusRect (focusRect:Object) : void;

		/// Indicates whether the text line contains any graphic elements.
		public function get hasGraphicElement () : Boolean;

		/// A Vector containing the TextLineMirrorRegion objects associated with the line, or null if none exist.
		public function get mirrorRegions () : Vector.<TextLineMirrorRegion>;

		/// The next TextLine in the TextBlock, or null if the current line is the last line in the block or the validity of the line is TextLineValidity.STATIC.
		public function get nextLine () : TextLine;

		/// The previous TextLine in the TextBlock, or null if the line is the first line in the block or the validity of the line is TextLineValidity.STATIC.
		public function get previousLine () : TextLine;

		/// The length of the raw text in the text block that became the line, including the U+FDEF characters representing graphic elements and any trailing spaces, which are part of the line but not are displayed.
		public function get rawTextLength () : int;

		/// The width that was specified to the TextBlock.createTextLine() method when it created the line.
		public function get specifiedWidth () : Number;

		public function set tabChildren (enable:Boolean) : void;

		public function set tabEnabled (enabled:Boolean) : void;

		public function set tabIndex (index:int) : void;

		/// The TextBlock containing this text line, or null if the validity of the line is TextLineValidity.STATIC.
		public function get textBlock () : TextBlock;

		/// The index of the first character of the line in the raw text of the text block.
		public function get textBlockBeginIndex () : int;

		/// The logical height of the text line, which is equal to ascent + descent.
		public function get textHeight () : Number;

		/// The logical width of the text line, which is the width that the text engine uses to lay out the line.
		public function get textWidth () : Number;

		/// The width of the line if it was not justified.
		public function get unjustifiedTextWidth () : Number;

		/// Specifies the current validity of the text line.
		public function get validity () : String;
		public function set validity (value:String) : void;

		/// Dumps the underlying contents of the TextLine as an XML string.
		public function dump () : String;

		/// Releases the atom data of the line for garbage collection.
		public function flushAtomData () : void;

		/// Gets the bidirectional level of the atom at the specified index.
		public function getAtomBidiLevel (atomIndex:int) : int;

		/// Gets the bounds of the atom at the specified index relative to the text line.
		public function getAtomBounds (atomIndex:int) : Rectangle;

		/// Gets the center of the atom as measured along the baseline at the specified index.
		public function getAtomCenter (atomIndex:int) : Number;

		/// Gets the graphic of the atom at the specified index, or null if the atom is a character.
		public function getAtomGraphic (atomIndex:int) : DisplayObject;

		/// Returns the index of the atom containing the character specified by the charIndex parameter, or -1 if the character does not contribute to any atom in the line.
		public function getAtomIndexAtCharIndex (charIndex:int) : int;

		/// Returns the index of the atom at the point specified by the x and y parameters, or -1 if no atom exists at that point.
		public function getAtomIndexAtPoint (stageX:Number, stageY:Number) : int;

		/// Gets the text block begin index of the atom at the specified index.
		public function getAtomTextBlockBeginIndex (atomIndex:int) : int;

		/// Gets the text block end index of the atom at the specified index.
		public function getAtomTextBlockEndIndex (atomIndex:int) : int;

		/// Gets the rotation of the atom at the specified index.
		public function getAtomTextRotation (atomIndex:int) : String;

		/// Indicates whether a word boundary occurs to the left of the atom at the specified index.
		public function getAtomWordBoundaryOnLeft (atomIndex:int) : Boolean;

		/// Gets the position of the specified baseline, relative to TextBlock.baselineZero.
		public function getBaselinePosition (baseline:String) : Number;

		/// Returns the first TextLineMirrorRegion on the line whose mirror property matches that specified by the mirror parameter, or null if no match exists.
		public function getMirrorRegion (mirror:EventDispatcher) : TextLineMirrorRegion;

		public function TextLine ();
	}
}
