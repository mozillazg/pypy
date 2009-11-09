package flash.display
{
	import flash.display.BitmapData;

	/// The Bitmap class represents display objects that represent bitmap images.
	public class Bitmap extends DisplayObject
	{
		/// The BitmapData object being referenced.
		public function get bitmapData () : BitmapData;
		public function set bitmapData (value:BitmapData) : void;

		/// Controls whether or not the Bitmap object is snapped to the nearest pixel.
		public function get pixelSnapping () : String;
		public function set pixelSnapping (value:String) : void;

		/// Controls whether or not the bitmap is smoothed when scaled.
		public function get smoothing () : Boolean;
		public function set smoothing (value:Boolean) : void;

		/// Initializes a Bitmap object to refer to the specified BitmapData object.
		public function Bitmap (bitmapData:BitmapData = null, pixelSnapping:String = "auto", smoothing:Boolean = false);
	}
}
