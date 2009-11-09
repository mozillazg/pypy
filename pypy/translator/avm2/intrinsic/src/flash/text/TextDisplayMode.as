package flash.text
{
	/// The TextDisplayMode class contains values that control the subpixel anti-aliasing of the advanced anti-aliasing system.
	public class TextDisplayMode extends Object
	{
		/// Forces Flash Player to display grayscale anti-aliasing.
		public static const CRT : String;
		/// Allows Flash Player to choose LCD or CRT mode.
		public static const DEFAULT : String;
		/// Forces Flash Player to use LCD subpixel anti-aliasing.
		public static const LCD : String;

		public function TextDisplayMode ();
	}
}
