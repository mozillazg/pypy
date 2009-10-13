package flash.filters
{
	import flash.geom.Rectangle;
	import flash.display.Shader;

	/// The ShaderFilter class applies a filter by executing a shader on the object being filtered.
	public class ShaderFilter extends BitmapFilter
	{
		/// The growth in pixels on the bottom side of the target object.
		public function get bottomExtension () : int;
		public function set bottomExtension (v:int) : void;

		/// The growth in pixels on the left side of the target object.
		public function get leftExtension () : int;
		public function set leftExtension (v:int) : void;

		/// The growth in pixels on the right side of the target object.
		public function get rightExtension () : int;
		public function set rightExtension (v:int) : void;

		/// The shader to use for this filter.
		public function get shader () : Shader;
		public function set shader (shader:Shader) : void;

		/// The growth in pixels on the top side of the target object.
		public function get topExtension () : int;
		public function set topExtension (v:int) : void;

		/// Creates a new shader filter.
		public function ShaderFilter (shader:Shader = null);
	}
}
