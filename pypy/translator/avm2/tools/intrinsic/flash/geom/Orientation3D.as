package flash.geom
{
	/// The Orientation3D class is an enumeration of constant values for representing the orientation styleof a Matrix3D object.
	public class Orientation3D extends Object
	{
		/// The axis angle orientation uses a combination of an axis and an angle to determine the orientation.
		public static const AXIS_ANGLE : String;
		/// Euler angles, the default orientation for decompose() and recompose() methods, defines the orientation with three separate angles of rotation for each axis.
		public static const EULER_ANGLES : String;
		/// The quaternion orientation uses complex numbers.
		public static const QUATERNION : String;

		public function Orientation3D ();
	}
}
