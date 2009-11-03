package flash.filters
{
	import flash.filters.BitmapFilter;

	/// The ConvolutionFilter class applies a matrix convolution filter effect.
	public class ConvolutionFilter extends BitmapFilter
	{
		/// The alpha transparency value of the substitute color.
		public function get alpha () : Number;
		public function set alpha (value:Number) : void;

		/// The amount of bias to add to the result of the matrix transformation.
		public function get bias () : Number;
		public function set bias (value:Number) : void;

		/// Indicates whether the image should be clamped.
		public function get clamp () : Boolean;
		public function set clamp (value:Boolean) : void;

		/// The hexadecimal color to substitute for pixels that are off the source image.
		public function get color () : uint;
		public function set color (value:uint) : void;

		/// The divisor used during matrix transformation.
		public function get divisor () : Number;
		public function set divisor (value:Number) : void;

		/// An array of values used for matrix transformation.
		public function get matrix () : Array;
		public function set matrix (value:Array) : void;

		/// The x dimension of the matrix (the number of columns in the matrix).
		public function get matrixX () : Number;
		public function set matrixX (value:Number) : void;

		/// The y dimension of the matrix (the number of rows in the matrix).
		public function get matrixY () : Number;
		public function set matrixY (value:Number) : void;

		/// Indicates if the alpha channel is preserved without the filter effect or if the convolution filter is applied to the alpha channel as well as the color channels.
		public function get preserveAlpha () : Boolean;
		public function set preserveAlpha (value:Boolean) : void;

		/// Returns a copy of this filter object.
		public function clone () : BitmapFilter;

		/// Initializes a ConvolutionFilter instance with the specified parameters.
		public function ConvolutionFilter (matrixX:Number = 0, matrixY:Number = 0, matrix:Array = null, divisor:Number = 1, bias:Number = 0, preserveAlpha:Boolean = true, clamp:Boolean = true, color:uint = 0, alpha:Number = 0);
	}
}
