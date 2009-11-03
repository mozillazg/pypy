package flash.filters
{
	import flash.filters.BitmapFilter;

	/// The BevelFilter class lets you add a bevel effect to display objects.
	public class BevelFilter extends BitmapFilter
	{
		/// The angle of the bevel.
		public function get angle () : Number;
		public function set angle (value:Number) : void;

		/// The amount of horizontal blur, in pixels.
		public function get blurX () : Number;
		public function set blurX (value:Number) : void;

		/// The amount of vertical blur, in pixels.
		public function get blurY () : Number;
		public function set blurY (value:Number) : void;

		/// The offset distance of the bevel.
		public function get distance () : Number;
		public function set distance (value:Number) : void;

		/// The alpha transparency value of the highlight color.
		public function get highlightAlpha () : Number;
		public function set highlightAlpha (value:Number) : void;

		/// The highlight color of the bevel.
		public function get highlightColor () : uint;
		public function set highlightColor (value:uint) : void;

		/// Applies a knockout effect (true), which effectively makes the object's fill transparent and reveals the background color of the document.
		public function get knockout () : Boolean;
		public function set knockout (value:Boolean) : void;

		/// The number of times to apply the filter.
		public function get quality () : int;
		public function set quality (value:int) : void;

		/// The alpha transparency value of the shadow color.
		public function get shadowAlpha () : Number;
		public function set shadowAlpha (value:Number) : void;

		/// The shadow color of the bevel.
		public function get shadowColor () : uint;
		public function set shadowColor (value:uint) : void;

		/// The strength of the imprint or spread.
		public function get strength () : Number;
		public function set strength (value:Number) : void;

		/// The placement of the bevel on the object.
		public function get type () : String;
		public function set type (value:String) : void;

		/// Initializes a new BevelFilter instance with the specified parameters.
		public function BevelFilter (distance:Number = 4, angle:Number = 45, highlightColor:uint = 16777215, highlightAlpha:Number = 1, shadowColor:uint = 0, shadowAlpha:Number = 1, blurX:Number = 4, blurY:Number = 4, strength:Number = 1, quality:int = 1, type:String = "inner", knockout:Boolean = false);

		/// Returns a copy of this filter object.
		public function clone () : BitmapFilter;
	}
}
