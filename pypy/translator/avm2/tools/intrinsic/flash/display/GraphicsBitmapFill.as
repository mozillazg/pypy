package flash.display
{
	import flash.geom.Matrix;
	import flash.display.BitmapData;

	/// Defines a bitmap fill.
	public class GraphicsBitmapFill extends Object implements IGraphicsFill, IGraphicsData
	{
		/// A transparent or opaque bitmap image.
		public var bitmapData : BitmapData;
		/// A matrix object (of the flash.geom.Matrix class) that defines transformations on the bitmap.
		public var matrix : Matrix;
		/// Specifies whether to repeat the bitmap image in a tiled pattern.
		public var repeat : Boolean;
		/// Specifies whether to apply a smoothing algorithm to the bitmap image.
		public var smooth : Boolean;

		/// Creates a new GraphicsBitmapFill object.
		public function GraphicsBitmapFill (bitmapData:BitmapData = null, matrix:Matrix = null, repeat:Boolean = true, smooth:Boolean = false);
	}
}
