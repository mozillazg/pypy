package flash.display
{
	import flash.geom.Matrix;

	/// Defines a gradient fill.
	public class GraphicsGradientFill extends Object implements IGraphicsFill, IGraphicsData
	{
		/// An array of alpha values for the corresponding colors in the colors array.
		public var alphas : Array;
		/// An array of RGB hexadecimal color values to use in the gradient.
		public var colors : Array;
		/// A number that controls the location of the focal point of the gradient.
		public var focalPointRatio : Number;
		/// A transformation matrix as defined by the Matrix class.
		public var matrix : Matrix;
		/// An array of color distribution ratios.
		public var ratios : Array;

		/// A value from the InterpolationMethod class that specifies which value to use.
		public function get interpolationMethod () : String;
		public function set interpolationMethod (value:String) : void;

		/// A value from the SpreadMethod class that specifies which spread method to use.
		public function get spreadMethod () : String;
		public function set spreadMethod (value:String) : void;

		/// A value from the GradientType class that specifies which gradient type to use.
		public function get type () : String;
		public function set type (value:String) : void;

		/// Creates a new GraphicsGradientFill object.
		public function GraphicsGradientFill (type:String = "linear", colors:Array = null, alphas:Array = null, ratios:Array = null, matrix:* = null, spreadMethod:* = "pad", interpolationMethod:String = "rgb", focalPointRatio:Number = 0);
	}
}
