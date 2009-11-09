package flash.filters
{
	import flash.filters.BitmapFilter;
	import flash.geom.Point;
	import flash.display.BitmapData;

	/// The DisplacementMapFilter class uses the pixel values from the specified BitmapData object (called the displacement map image) to perform a displacement of an object.
	public class DisplacementMapFilter extends BitmapFilter
	{
		/// Specifies the alpha transparency value to use for out-of-bounds displacements.
		public function get alpha () : Number;
		public function set alpha (value:Number) : void;

		/// Specifies what color to use for out-of-bounds displacements.
		public function get color () : uint;
		public function set color (value:uint) : void;

		/// Describes which color channel to use in the map image to displace the x result.
		public function get componentX () : uint;
		public function set componentX (value:uint) : void;

		/// Describes which color channel to use in the map image to displace the y result.
		public function get componentY () : uint;
		public function set componentY (value:uint) : void;

		/// A BitmapData object containing the displacement map data.
		public function get mapBitmap () : BitmapData;
		public function set mapBitmap (value:BitmapData) : void;

		/// A value that contains the offset of the upper-left corner of the target display object from the upper-left corner of the map image.
		public function get mapPoint () : Point;
		public function set mapPoint (value:Point) : void;

		/// The mode for the filter.
		public function get mode () : String;
		public function set mode (value:String) : void;

		/// The multiplier to use to scale the x displacement result from the map calculation.
		public function get scaleX () : Number;
		public function set scaleX (value:Number) : void;

		/// The multiplier to use to scale the y displacement result from the map calculation.
		public function get scaleY () : Number;
		public function set scaleY (value:Number) : void;

		/// Returns a copy of this filter object.
		public function clone () : BitmapFilter;

		/// Initializes a DisplacementMapFilter instance.
		public function DisplacementMapFilter (mapBitmap:BitmapData = null, mapPoint:Point = null, componentX:uint = 0, componentY:uint = 0, scaleX:Number = 0, scaleY:Number = 0, mode:String = "wrap", color:uint = 0, alpha:Number = 0);
	}
}
