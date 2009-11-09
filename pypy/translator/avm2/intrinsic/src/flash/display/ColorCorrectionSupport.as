package flash.display
{
	/// The ColorCorrectionSupport class provides values for the flash.display.Stage.colorCorrectionSupport property.
	public class ColorCorrectionSupport extends Object
	{
		/// Color correction is supported, but off by default.
		public static const DEFAULT_OFF : String;
		/// Color correction is supported, and on by default.
		public static const DEFAULT_ON : String;
		/// Color correction is not supported by the host environment.
		public static const UNSUPPORTED : String;

		public function ColorCorrectionSupport ();
	}
}
