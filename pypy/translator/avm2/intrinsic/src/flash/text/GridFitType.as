package flash.text
{
	/// The GridFitType class defines values for grid fitting in the TextField class.
	public class GridFitType extends Object
	{
		/// Doesn't set grid fitting.
		public static const NONE : String;
		/// Fits strong horizontal and vertical lines to the pixel grid.
		public static const PIXEL : String;
		/// Fits strong horizontal and vertical lines to the sub-pixel grid on LCD monitors.
		public static const SUBPIXEL : String;

		public function GridFitType ();
	}
}
