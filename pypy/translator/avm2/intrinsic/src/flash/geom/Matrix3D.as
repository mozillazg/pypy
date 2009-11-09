package flash.geom
{
	import flash.geom.Matrix3D;
	import flash.geom.Vector3D;

	/// The Matrix3D class represents a transformation matrix that determines the position and orientation of the three-dimensional display object.
	public class Matrix3D extends Object
	{
		/// A Number that determines whether a matrix is invertible.
		public function get determinant () : Number;

		/// A Vector3D object that holds the position, the three-dimensional coordinate (x,y,z) of a display object within the transformation's frame of reference.
		public function get position () : Vector3D;
		public function set position (pos:Vector3D) : void;

		/// A Vector of 16 Numbers, where every four elements can be a row or a column of a 4x4 matrix.
		public function get rawData () : Vector.<Number>;
		public function set rawData (v:Vector.<Number>) : void;

		/// Appends the matrix by multiplying another Matrix3D object by the current Matrix3D object.
		public function append (lhs:Matrix3D) : void;

		/// Appends an incremental rotation to a Matrix3D object.
		public function appendRotation (degrees:Number, axis:Vector3D, pivotPoint:Vector3D = null) : void;

		/// Appends an incremental scale change along the x, y, and z axes to a Matrix3D object.
		public function appendScale (xScale:Number, yScale:Number, zScale:Number) : void;

		/// Appends an incremental translation, a repositioning along the x, y, and z axes, to a Matrix3D object.
		public function appendTranslation (x:Number, y:Number, z:Number) : void;

		/// Returns a new Matrix3D object that is an exact copy of the current Matrix3D object.
		public function clone () : Matrix3D;

		/// Returns the transformation matrix's translation, rotation, and scale settings as a Vector of three Vector3D objects.
		public function decompose (orientationStyle:String = "eulerAngles") : Vector.<Vector3D>;

		/// Uses the transformation matrix without its translation elements to transform a Vector3D object from one space coordinate to another.
		public function deltaTransformVector (v:Vector3D) : Vector3D;

		/// Converts the current matrix to an identity or unit matrix.
		public function identity () : void;

		/// Interpolates a display object a percent point closer to a target display object.
		public static function interpolate (thisMat:Matrix3D, toMat:Matrix3D, percent:Number) : Matrix3D;

		/// Interpolates the display object's matrix a percent closer to a target's matrix.
		public function interpolateTo (toMat:Matrix3D, percent:Number) : void;

		/// Inverts the current matrix.
		public function invert () : Boolean;

		/// Creates a Matrix3D object.
		public function Matrix3D (v:Vector.<Number> = null);

		/// Rotates the display object so that it faces a specified position.
		public function pointAt (pos:Vector3D, at:Vector3D = null, up:Vector3D = null) : void;

		/// Prepends a matrix by multiplying the current Matrix3D object by another Matrix3D object.
		public function prepend (rhs:Matrix3D) : void;

		/// Prepends an incremental rotation to a Matrix3D object.
		public function prependRotation (degrees:Number, axis:Vector3D, pivotPoint:Vector3D = null) : void;

		/// Prepends an incremental scale change along the x, y, and z axes to a Matrix3D object.
		public function prependScale (xScale:Number, yScale:Number, zScale:Number) : void;

		/// Prepends an incremental translation, a repositioning along the x, y, and z axes, to a Matrix3D object.
		public function prependTranslation (x:Number, y:Number, z:Number) : void;

		/// Sets the transformation matrix's translation, rotation, and scale settings.
		public function recompose (components:Vector.<Vector3D>, orientationStyle:String = "eulerAngles") : Boolean;

		/// Uses the transformation matrix to transform a Vector3D object from one space coordinate to another.
		public function transformVector (v:Vector3D) : Vector3D;

		/// Uses the transformation matrix to transform a Vector of Numbers from one coordinate space to another.
		public function transformVectors (vin:Vector.<Number>, vout:Vector.<Number>) : void;

		/// Converts the current Matrix3D object to a matrix where the rows and columns are swapped.
		public function transpose () : void;
	}
}
