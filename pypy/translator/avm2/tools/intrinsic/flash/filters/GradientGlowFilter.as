package flash.filters
{
	import flash.filters.BitmapFilter;

	/// The GradientGlowFilter class lets you apply a gradient glow effect to display objects.
	public class GradientGlowFilter extends BitmapFilter
	{
		/// An array of alpha transparency values for the corresponding colors in the colors array.
		public function get alphas () : Array;
		public function set alphas (value:Array) : void;

		/// The angle, in degrees.
		public function get angle () : Number;
		public function set angle (value:Number) : void;

		/// The amount of horizontal blur.
		public function get blurX () : Number;
		public function set blurX (value:Number) : void;

		/// The amount of vertical blur.
		public function get blurY () : Number;
		public function set blurY (value:Number) : void;

		/// An array of colors that defines a gradient.
		public function get colors () : Array;
		public function set colors (value:Array) : void;

		/// The offset distance of the glow.
		public function get distance () : Number;
		public function set distance (value:Number) : void;

		/// Specifies whether the object has a knockout effect.
		public function get knockout () : Boolean;
		public function set knockout (value:Boolean) : void;

		/// The number of times to apply the filter.
		public function get quality () : int;
		public function set quality (value:int) : void;

		/// An array of color distribution ratios for the corresponding colors in the colors array.
		public function get ratios () : Array;
		public function set ratios (value:Array) : void;

		/// The strength of the imprint or spread.
		public function get strength () : Number;
		public function set strength (value:Number) : void;

		/// The placement of the filter effect.
		public function get type () : String;
		public function set type (value:String) : void;

		/// Returns a copy of this filter object.
		public function clone () : BitmapFilter;

		/// Initializes the filter with the specified parameters.
		public function GradientGlowFilter (distance:Number = 4, angle:Number = 45, colors:Array = null, alphas:Array = null, ratios:Array = null, blurX:Number = 4, blurY:Number = 4, strength:Number = 1, quality:int = 1, type:String = "inner", knockout:Boolean = false);
	}
}
