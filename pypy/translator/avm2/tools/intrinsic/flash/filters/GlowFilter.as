package flash.filters
{
	import flash.filters.BitmapFilter;

	/// The GlowFilter class lets you apply a glow effect to display objects.
	public class GlowFilter extends BitmapFilter
	{
		/// The alpha transparency value for the color.
		public function get alpha () : Number;
		public function set alpha (value:Number) : void;

		/// The amount of horizontal blur.
		public function get blurX () : Number;
		public function set blurX (value:Number) : void;

		/// The amount of vertical blur.
		public function get blurY () : Number;
		public function set blurY (value:Number) : void;

		/// The color of the glow.
		public function get color () : uint;
		public function set color (value:uint) : void;

		/// Specifies whether the glow is an inner glow.
		public function get inner () : Boolean;
		public function set inner (value:Boolean) : void;

		/// Specifies whether the object has a knockout effect.
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

		/// Initializes a new GlowFilter instance with the specified parameters.
		public function GlowFilter (color:uint = 16711680, alpha:Number = 1, blurX:Number = 6, blurY:Number = 6, strength:Number = 2, quality:int = 1, inner:Boolean = false, knockout:Boolean = false);
	}
}
