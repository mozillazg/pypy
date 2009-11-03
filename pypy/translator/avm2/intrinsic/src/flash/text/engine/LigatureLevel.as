package flash.text.engine
{
	/// The LigatureLevel class is an enumeration of constant values used in setting the ligatureLevel property of the ElementFormat class.
	public class LigatureLevel extends Object
	{
		/// Used to specify common ligatures.
		public static const COMMON : String;
		/// Used to specify exotic ligatures.
		public static const EXOTIC : String;
		/// Used to specify minimum ligatures.
		public static const MINIMUM : String;
		/// Used to specify no ligatures.
		public static const NONE : String;
		/// Used to specify uncommon ligatures.
		public static const UNCOMMON : String;

		public function LigatureLevel ();
	}
}
