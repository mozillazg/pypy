package flash.text.engine
{
	/// The TypographicCase class is an enumeration of constant values for setting the typographicCase property of the ElementFormat class.
	public class TypographicCase extends Object
	{
		/// Specifies that spacing is adjusted for uppercase characters on output.
		public static const CAPS : String;
		/// Specifies that all lowercase characters use small-caps glyphs on output.
		public static const CAPS_AND_SMALL_CAPS : String;
		/// Specifies default typographic case.
		public static const DEFAULT : String;
		/// Specifies that all characters use lowercase glyphs on output.
		public static const LOWERCASE : String;
		/// Specifies that uppercase characters use small-caps glyphs on output.
		public static const SMALL_CAPS : String;
		/// Specifies that uppercase characters use title glyphs on output.
		public static const TITLE : String;
		/// Specifies that all characters use uppercase glyphs on output.
		public static const UPPERCASE : String;

		public function TypographicCase ();
	}
}
