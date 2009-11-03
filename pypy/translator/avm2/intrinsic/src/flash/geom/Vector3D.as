package flash.geom
{
	import flash.geom.Vector3D;

	/// The Vector3D class represents a point or a location in the three-dimensional space using the Cartesian coordinates x, y, and z.
	public class Vector3D extends Object
	{
		/// The fourth element of a Vector3D object (in addition to the x, y, and z properties) can hold data such as the angle of rotation.
		public var w : Number;
		/// The first element of a Vector3D object, such as the x coordinate of a point in the three-dimensional space.
		public var x : Number;
		/// The x axis defined as a Vector3D object with coordinates (1,0,0).
		public static const X_AXIS : Vector3D;
		/// The second element of a Vector3D object, such as the y coordinate of a point in the three-dimensional space.
		public var y : Number;
		/// The y axis defined as a Vector3D object with coordinates (0,1,0).
		public static const Y_AXIS : Vector3D;
		/// The third element of a Vector3D object, such as the z coordinate of a point in three-dimensional space.
		public var z : Number;
		/// The z axis defined as a Vector3D object with coordinates (0,0,1).
		public static const Z_AXIS : Vector3D;

		/// The length, magnitude, of the current Vector3D object from the origin (0,0,0) to the object's x, y, and z coordinates.
		public function get length () : Number;

		/// The square of the length of the current Vector3D object, calculated using the x, y, and z properties.
		public function get lengthSquared () : Number;

		/// Adds the current Vector3D object to another in order to create a new Vector3D object.
		public function add (a:Vector3D) : Vector3D;

		/// Returns the angle in radians between two vectors.
		public static function angleBetween (a:Vector3D, b:Vector3D) : Number;

		/// Returns a new Vector3D object that is an exact copy of the current Vector3D object.
		public function clone () : Vector3D;

		/// Returns a new Vector3D object that is perpendicular (at a right angle) to the current Vector3D and another Vector3D object.
		public function crossProduct (a:Vector3D) : Vector3D;

		/// Decrements the current Vector3D object by another Vector3D object.
		public function decrementBy (a:Vector3D) : void;

		/// Returns the distance between two Vector3D objects.
		public static function distance (pt1:Vector3D, pt2:Vector3D) : Number;

		/// Returns the dot product of current and another Vector3D object.
		public function dotProduct (a:Vector3D) : Number;

		/// Determines whether two Vector3D objects are equal by comparing the x, y, and z elements of the current Vector3D object with a specified Vector3D object.
		public function equals (toCompare:Vector3D, allFour:Boolean = false) : Boolean;

		/// Increments the current Vector3D object by another Vector3D object.
		public function incrementBy (a:Vector3D) : void;

		/// Compares the elements of the current Vector3D object with the elements of a specified Vector3D object to determine whether they are nearly equal.
		public function nearEquals (toCompare:Vector3D, tolerance:Number, allFour:Boolean = false) : Boolean;

		/// Sets the current Vector3D object to its inverse.
		public function negate () : void;

		/// Converts a Vector3D object to a unit vector by dividing the first three elements (x, y, z) by the length of the vector.
		public function normalize () : Number;

		/// Divides the value of the x, y, and z properties of the current Vector3D object by the value of its w property.
		public function project () : void;

		/// Scales the current Vector3D object by a scalar, a magnitude.
		public function scaleBy (s:Number) : void;

		/// Subtracts the current Vector3D from another Vector3D object in order to create a new Vector3D object.
		public function subtract (a:Vector3D) : Vector3D;

		/// Returns a string representation of the current Vector3D object.
		public function toString () : String;

		/// Creates an instance of a Vector3D object.
		public function Vector3D (x:Number = 0, y:Number = 0, z:Number = 0, w:Number = 0);
	}
}
