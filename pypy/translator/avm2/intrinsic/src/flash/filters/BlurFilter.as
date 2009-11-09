package flash.filters
{
	import flash.filters.BitmapFilter;

	/// The BlurFilter class lets you apply a blur visual effect to display objects.
	public class BlurFilter extends BitmapFilter
	{
		/// The amount of horizontal blur.
		public function get blurX () : Number;
		public function set blurX (value:Number) : void;

		/// The amount of vertical blur.
		public function get blurY () : Number;
		public function set blurY (value:Number) : void;

		/// The number of times to perform the blur.
		public function get quality () : int;
		public function set quality (value:int) : void;

		/// Initializes the filter.
		public function BlurFilter (blurX:Number = 4, blurY:Number = 4, quality:int = 1);

		/// Returns a copy of this filter object.
		public function clone () : BitmapFilter;
	}
}
