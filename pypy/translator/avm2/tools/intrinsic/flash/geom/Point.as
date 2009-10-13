package flash.geom
{
	import flash.geom.Point;

	/// The Point object represents a location in a two-dimensional coordinate system, where x represents the horizontal axis and y represents the vertical axis.
	public class Point extends Object
	{
		/// The horizontal coordinate of the point.
		public var x : Number;
		/// The vertical coordinate of the point.
		public var y : Number;

		/// The length of the line segment from (0,0) to this point.
		public function get length () : Number;

		/// Adds the coordinates of another point to the coordinates of this point to create a new point.
		public function add (v:Point) : Point;

		/// Creates a copy of the Point object.
		public function clone () : Point;

		/// Returns the distance between pt1 and pt2.
		public static function distance (pt1:Point, pt2:Point) : Number;

		/// Determines whether two points are equal.
		public function equals (toCompare:Point) : Boolean;

		/// Determines a point between two specified points.
		public static function interpolate (pt1:Point, pt2:Point, f:Number) : Point;

		/// Scales the line segment between (0,0) and the current point to a set length.
		public function normalize (thickness:Number) : void;

		/// Offsets the Point object by the specified amount.
		public function offset (dx:Number, dy:Number) : void;

		/// Creates a new point.
		public function Point (x:Number = 0, y:Number = 0);

		/// Converts a pair of polar coordinates to a Cartesian point coordinate.
		public static function polar (len:Number, angle:Number) : Point;

		/// Subtracts the coordinates of another point from the coordinates of this point to create a new point.
		public function subtract (v:Point) : Point;

		/// Returns a string that contains the values of the x and y coordinates.
		public function toString () : String;
	}
}
