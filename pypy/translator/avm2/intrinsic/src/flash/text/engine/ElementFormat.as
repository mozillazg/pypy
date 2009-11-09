package flash.text.engine
{
	import flash.text.engine.FontDescription;
	import flash.text.engine.ElementFormat;
	import flash.text.engine.FontMetrics;

	/// The ElementFormat class represents formatting information which can be applied to a ContentElement.
	public class ElementFormat extends Object
	{
		/// Specifies which of the baselines of the line containing the element the dominantBaseline snaps to, thus determining the vertical position of the element in the line.
		public function get alignmentBaseline () : String;
		public function set alignmentBaseline (alignmentBaseline:String) : void;

		/// Provides a way for the author to automatically set the alpha property of all line atoms based on the element format to the specified Number.
		public function get alpha () : Number;
		public function set alpha (value:Number) : void;

		/// Indicates the baseline shift for the element in pixels.
		public function get baselineShift () : Number;
		public function set baselineShift (value:Number) : void;

		/// The line break opportunity applied to this text.
		public function get breakOpportunity () : String;
		public function set breakOpportunity (opportunityType:String) : void;

		/// Indicates the color of the text.
		public function get color () : uint;
		public function set color (value:uint) : void;

		/// The digit case used for this text.
		public function get digitCase () : String;
		public function set digitCase (digitCaseType:String) : void;

		/// The digit width used for this text.
		public function get digitWidth () : String;
		public function set digitWidth (digitWidthType:String) : void;

		/// Specifies which of the baselines of the element snaps to the alignmentBaseline to determine the vertical position of the element on the line.
		public function get dominantBaseline () : String;
		public function set dominantBaseline (dominantBaseline:String) : void;

		/// An object which encapsulates properties necessary to describe a font.
		public function get fontDescription () : FontDescription;
		public function set fontDescription (value:FontDescription) : void;

		/// The point size of text.
		public function get fontSize () : Number;
		public function set fontSize (value:Number) : void;

		/// The kerning used for this text.
		public function get kerning () : String;
		public function set kerning (value:String) : void;

		/// The ligature level used for this text.
		public function get ligatureLevel () : String;
		public function set ligatureLevel (ligatureLevelType:String) : void;

		/// The locale of the text.
		public function get locale () : String;
		public function set locale (value:String) : void;

		/// Indicates whether or not the ElementFormat is locked.
		public function get locked () : Boolean;
		public function set locked (value:Boolean) : void;

		/// Sets the rotation applied to individual glyphs.
		public function get textRotation () : String;
		public function set textRotation (value:String) : void;

		/// The tracking or manual kerning applied to the left of each glyph in pixels.
		public function get trackingLeft () : Number;
		public function set trackingLeft (value:Number) : void;

		/// The tracking or manual kerning applied to the right of each glyph in pixels.
		public function get trackingRight () : Number;
		public function set trackingRight (value:Number) : void;

		/// The typographic case used for this text.
		public function get typographicCase () : String;
		public function set typographicCase (typographicCaseType:String) : void;

		/// Constructs an unlocked, cloned copy of the ElementFormat.
		public function clone () : ElementFormat;

		/// Creates an ElementFormat object.
		public function ElementFormat (fontDescription:FontDescription = null, fontSize:Number = 12, color:uint = 0, alpha:Number = 1, textRotation:String = "auto", dominantBaseline:String = "roman", alignmentBaseline:String = "useDominantBaseline", baselineShift:Number = 0, kerning:String = "on", trackingRight:Number = 0, trackingLeft:Number = 0, locale:String = "en", breakOpportunity:String = "auto", digitCase:String = "default", digitWidth:String = "default", ligatureLevel:String = "common", typographicCase:String = "default");

		/// Returns a FontMetrics object with properties which describe the emBox, strikethrough position, strikethrough thickness, underline position, and underline thickness for the font specified by fontDescription and fontSize.
		public function getFontMetrics () : FontMetrics;
	}
}
