package flash.ui
{
	/// The KeyLocation class contains constants that indicate the location of a key pressed on the keyboard.
	public class KeyLocation extends Object
	{
		/// Indicates the key activated is in the left key location (there is more than one possible location for this key).
		public static const LEFT : uint;
		/// Indicates the key activation originated on the numeric keypad or with a virtual key corresponding to the numeric keypad.
		public static const NUM_PAD : uint;
		/// Indicates the key activated is in the right key location (there is more than one possible location for this key).
		public static const RIGHT : uint;
		/// Indicates the key activation is not distinguished as the left or right version of the key, and did not originate on the numeric keypad (or did not originate with a virtual key corresponding to the numeric keypad).
		public static const STANDARD : uint;

		public function KeyLocation ();
	}
}
