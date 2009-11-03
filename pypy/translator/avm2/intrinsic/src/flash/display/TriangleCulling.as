package flash.display
{
	/// Defines codes for culling algorithms that determine which triangles not to render when drawing triangle paths.
	public class TriangleCulling extends Object
	{
		/// Specifies culling of all triangles facing toward the current view point.
		public static const NEGATIVE : String;
		/// Specifies no culling.
		public static const NONE : String;
		/// Specifies culling of all triangles facing away from the current view point.
		public static const POSITIVE : String;

		public function TriangleCulling ();
	}
}
