package flash.display
{
	/// The PixelSnapping class is an enumeration of constant values for setting the pixel snapping options by using the pixelSnapping property of a Bitmap object.
	public class PixelSnapping extends Object
	{
		/// A constant value used in the pixelSnapping property of a Bitmap object to specify that the bitmap image is always snapped to the nearest pixel, independent of any transformation.
		public static const ALWAYS : String;
		/// A constant value used in the pixelSnapping property of a Bitmap object to specify that the bitmap image is snapped to the nearest pixel if it is drawn with no rotation or skew and it is drawn at a scale factor of 99.9% to 100.1%.
		public static const AUTO : String;
		/// A constant value used in the pixelSnapping property of a Bitmap object to specify that no pixel snapping occurs.
		public static const NEVER : String;

		public function PixelSnapping ();
	}
}
