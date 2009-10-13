package flash.text
{
	/// The TextRenderer class provides functionality for the advanced anti-aliasing capability of embedded fonts.
	public class TextRenderer extends Object
	{
		public static function get antiAliasType () : String;
		public static function set antiAliasType (value:String) : void;

		/// Controls the rendering of advanced anti-aliased text.
		public static function get displayMode () : String;
		public static function set displayMode (value:String) : void;

		/// The adaptively sampled distance fields (ADFs) quality level for advanced anti-aliasing.
		public static function get maxLevel () : int;
		public static function set maxLevel (value:int) : void;

		/// Sets a custom continuous stroke modulation (CSM) lookup table for a font.
		public static function setAdvancedAntiAliasingTable (fontName:String, fontStyle:String, colorType:String, advancedAntiAliasingTable:Array) : void;

		public function TextRenderer ();
	}
}
