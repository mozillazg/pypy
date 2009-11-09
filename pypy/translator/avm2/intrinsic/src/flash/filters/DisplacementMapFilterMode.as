package flash.filters
{
	/// The DisplacementMapFilterMode class provides values for the mode propertyof the DisplacementMapFilter class.
	public class DisplacementMapFilterMode extends Object
	{
		/// Clamps the displacement value to the edge of the source image.
		public static const CLAMP : String;
		/// If the displacement value is outside the image, substitutes the values in the color and alpha properties.
		public static const COLOR : String;
		/// If the displacement value is out of range, ignores the displacement and uses the source pixel.
		public static const IGNORE : String;
		/// Wraps the displacement value to the other side of the source image.
		public static const WRAP : String;

		public function DisplacementMapFilterMode ();
	}
}
