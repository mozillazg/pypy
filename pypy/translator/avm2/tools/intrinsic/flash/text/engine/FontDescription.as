package flash.text.engine
{
	import flash.text.engine.FontDescription;

	/// The FontDescription class represents properties necessary to describe a font.
	public class FontDescription extends Object
	{
		/// The type of CFF hinting used for this text.
		public function get cffHinting () : String;
		public function set cffHinting (value:String) : void;

		/// Specifies how the font should be looked up.
		public function get fontLookup () : String;
		public function set fontLookup (value:String) : void;

		/// The name of the font to use, or a comma-separated list of font names.
		public function get fontName () : String;
		public function set fontName (value:String) : void;

		/// Specifies the font posture.
		public function get fontPosture () : String;
		public function set fontPosture (value:String) : void;

		/// Specifies the font weight.
		public function get fontWeight () : String;
		public function set fontWeight (value:String) : void;

		/// Indicates whether or not the FontDescription is locked.
		public function get locked () : Boolean;
		public function set locked (value:Boolean) : void;

		/// The rendering mode used for this text.
		public function get renderingMode () : String;
		public function set renderingMode (value:String) : void;

		/// Constructs an unlocked, cloned copy of the FontDescription.
		public function clone () : FontDescription;

		/// Creates a FontDescription object.
		public function FontDescription (fontName:String = "_serif", fontWeight:String = "normal", fontPosture:String = "normal", fontLookup:String = "device", renderingMode:String = "cff", cffHinting:String = "horizontalStem");

		/// Returns true if an embedded font is available with the specified fontName, fontWeight, and fontPosture where Font.fontType is flash.text.FontType.EMBEDDED_CFF.
		public static function isFontCompatible (fontName:String, fontWeight:String, fontPosture:String) : Boolean;
	}
}
