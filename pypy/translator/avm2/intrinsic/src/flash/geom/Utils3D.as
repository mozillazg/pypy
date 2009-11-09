package flash.geom
{
	import flash.geom.Matrix3D;
	import flash.geom.Vector3D;

	/// The Utils3D class contains static methods that simplify the implementation of certain three-dimensional matrix operations.
	public class Utils3D extends Object
	{
		/// Interpolates the orientation of an object toward a position.
		public static function pointTowards (percent:Number, mat:Matrix3D, pos:Vector3D, at:Vector3D = null, up:Vector3D = null) : Matrix3D;

		/// Using a projection Matrix3D object, projects a Vector3D object from one space coordinate to another.
		public static function projectVector (m:Matrix3D, v:Vector3D) : Vector3D;

		/// Projects a Vector of three-dimensional space coordinates to a Vector of two-dimensional space coordinates.
		public static function projectVectors (m:Matrix3D, verts:Vector.<Number>, projectedVerts:Vector.<Number>, uvts:Vector.<Number>) : void;

		public function Utils3D ();
	}
}
