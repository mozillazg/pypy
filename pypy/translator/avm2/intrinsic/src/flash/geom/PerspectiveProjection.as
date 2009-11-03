package flash.geom
{
	import flash.geom.Point;
	import flash.geom.Matrix3D;

	/// The PerspectiveProjection class provides an easy way to assign or modify the perspective transformations of a display object and all of its children.
	public class PerspectiveProjection extends Object
	{
		/// Specifies an angle, as a degree between 0 and 180, for the field of view in three dimensions.
		public function get fieldOfView () : Number;
		public function set fieldOfView (fieldOfViewAngleInDegrees:Number) : void;

		/// The distance between the eye or the viewpoint's origin (0,0,0) and the display object located in the z axis.
		public function get focalLength () : Number;
		public function set focalLength (value:Number) : void;

		/// A two-dimensional point representing the center of the projection, the vanishing point for the display object.
		public function get projectionCenter () : Point;
		public function set projectionCenter (p:Point) : void;

		/// Creates an instance of a PerspectiveProjection object.
		public function PerspectiveProjection ();

		/// Returns the underlying Matrix3D object of the display object.
		public function toMatrix3D () : Matrix3D;
	}
}
