package flash.text.engine
{
	/// The Kerning class is an enumeration of constant values used with ElementFormat.kerning.
	public class Kerning extends Object
	{
		/// Used to indicate kerning is enabled only for characters appropriate in Asian typography.
		public static const AUTO : String;
		/// Used to indicate kerning is disabled.
		public static const OFF : String;
		/// Used to indicate kerning is enabled.
		public static const ON : String;

		public function Kerning ();
	}
}
