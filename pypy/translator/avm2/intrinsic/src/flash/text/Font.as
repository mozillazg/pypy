package flash.text
{
	/// The Font class is used to manage embedded fonts in SWF files.
	public class Font extends Object
	{
		/// The name of an embedded font.
		public function get fontName () : String;

		/// The style of the font.
		public function get fontStyle () : String;

		/// The type of the font.
		public function get fontType () : String;

		/// Specifies whether to provide a list of the currently available embedded fonts.
		public static function enumerateFonts (enumerateDeviceFonts:Boolean = false) : Array;

		public function Font ();

		/// Specifies whether a provided string can be displayed using the currently assigned font.
		public function hasGlyphs (str:String) : Boolean;

		/// Registers a font class in the global font list.
		public static function registerFont (font:Class) : void;
	}
}
