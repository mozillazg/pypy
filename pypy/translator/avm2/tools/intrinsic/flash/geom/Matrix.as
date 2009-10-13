package flash.geom
{
	import flash.geom.Matrix;
	import flash.geom.Point;

	/// The Matrix class represents a transformation matrix that determines how to map points from one coordinate space to another.
	public class Matrix extends Object
	{
		/// The value that affects the positioning of pixels along the x axis when scaling or rotating an image.
		public var a : Number;
		/// The value that affects the positioning of pixels along the y axis when rotating or skewing an image.
		public var b : Number;
		/// The value that affects the positioning of pixels along the x axis when rotating or skewing an image.
		public var c : Number;
		/// The value that affects the positioning of pixels along the y axis when scaling or rotating an image.
		public var d : Number;
		/// The distance by which to translate each point along the x axis.
		public var tx : Number;
		/// The distance by which to translate each point along the y axis.
		public var ty : Number;

		/// Returns a new Matrix object that is a copy of the current matrix.
		public function clone () : Matrix;

		/// Concatenates a matrix with the current matrix, effectively combining the geometric effects of the two.
		public function concat (m:Matrix) : void;

		/// Creates a Matrix with scaling, rotation, and translation values.
		public function createBox (scaleX:Number, scaleY:Number, rotation:Number = 0, tx:Number = 0, ty:Number = 0) : void;

		/// Creates the specific style of matrix expected by the beginGradientFill() method of the Graphics class.
		public function createGradientBox (width:Number, height:Number, rotation:Number = 0, tx:Number = 0, ty:Number = 0) : void;

		/// Given a point in the pretransform coordinate space, returns the coordinates of that point after the transformation occurs.
		public function deltaTransformPoint (point:Point) : Point;

		/// Sets each matrix property to a value that causes a null transformation.
		public function identity () : void;

		/// Performs the opposite transformation of the original matrix.
		public function invert () : void;

		/// Creates a new two-dimensional Matrix object.
		public function Matrix (a:Number = 1, b:Number = 0, c:Number = 0, d:Number = 1, tx:Number = 0, ty:Number = 0);

		/// Applies a rotation transformation to the Matrix object.
		public function rotate (angle:Number) : void;

		/// Applies a scaling transformation to the matrix.
		public function scale (sx:Number, sy:Number) : void;

		/// Returns a text value listing the properties of this Matrix object.
		public function toString () : String;

		/// Returns the result of a geometric transformation to a Point object.
		public function transformPoint (point:Point) : Point;

		/// A transformation that moves an object along the x and y axes.
		public function translate (dx:Number, dy:Number) : void;
	}
}
