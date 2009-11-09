package flash.display
{
	/// The ColorCorrection class provides values for the flash.display.Stage.colorCorrection property.
	public class ColorCorrection extends Object
	{
		/// Uses the host's default color correction.
		public static const DEFAULT : String;
		/// Turns off color correction regardless of the player host environment.
		public static const OFF : String;
		/// Turns on color correction regardless of the player host environment, if available.
		public static const ON : String;

		public function ColorCorrection ();
	}
}
