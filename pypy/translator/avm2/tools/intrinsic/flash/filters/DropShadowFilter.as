package flash.filters
{
	import flash.filters.BitmapFilter;

	/// The DropShadowFilter class lets you add a drop shadow to display objects.
	public class DropShadowFilter extends BitmapFilter
	{
		/// The alpha transparency value for the shadow color.
		public function get alpha () : Number;
		public function set alpha (value:Number) : void;

		/// The angle of the shadow.
		public function get angle () : Number;
		public function set angle (value:Number) : void;

		/// The amount of horizontal blur.
		public function get blurX () : Number;
		public function set blurX (value:Number) : void;

		/// The amount of vertical blur.
		public function get blurY () : Number;
		public function set blurY (value:Number) : void;

		/// The color of the shadow.
		public function get color () : uint;
		public function set color (value:uint) : void;

		/// The offset distance for the shadow, in pixels.
		public function get distance () : Number;
		public function set distance (value:Number) : void;

		/// Indicates whether or not the object is hidden.
		public function get hideObject () : Boolean;
		public function set hideObject (value:Boolean) : void;

		/// Indicates whether or not the shadow is an inner shadow.
		public function get inner () : Boolean;
		public function set inner (value:Boolean) : void;

		/// Applies a knockout effect (true), which effectively makes the object's fill transparent and reveals the background color of the document.
		public function get knockout () : Boolean;
		public function set knockout (value:Boolean) : void;

		/// The number of times to apply the filter.
		public function get quality () : int;
		public function set quality (value:int) : void;

		/// The strength of the imprint or spread.
		public function get strength () : Number;
		public function set strength (value:Number) : void;

		/// Returns a copy of this filter object.
		public function clone () : BitmapFilter;

		/// Creates a new DropShadowFilter instance with the specified parameters.
		public function DropShadowFilter (distance:Number = 4, angle:Number = 45, color:uint = 0, alpha:Number = 1, blurX:Number = 4, blurY:Number = 4, strength:Number = 1, quality:int = 1, inner:Boolean = false, knockout:Boolean = false, hideObject:Boolean = false);
	}
}
