package flash.text
{
	/// The FontType class contains the enumerated constants "embedded" and "device" for the fontType property of the Font class.
	public class FontType extends Object
	{
		/// Indicates that this is a device font.
		public static const DEVICE : String;
		/// Indicates that this is an embedded font.
		public static const EMBEDDED : String;
		/// Indicates that this is an embedded CFF font.
		public static const EMBEDDED_CFF : String;

		public function FontType ();
	}
}
