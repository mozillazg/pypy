package flash.display
{
	/// A ShaderInput instance represents a single input image for a shader kernel.
	public class ShaderInput extends Object
	{
		/// The number of channels that a shader input expects.
		public function get channels () : int;

		/// The height of the shader input.
		public function get height () : int;
		public function set height (value:int) : void;

		/// The zero-based index of the input in the shader, indicating the order of the input definitions in the shader.
		public function get index () : int;

		/// The input data that is used when the shader executes.
		public function get input () : Object;
		public function set input (input:Object) : void;

		/// The width of the shader input.
		public function get width () : int;
		public function set width (value:int) : void;

		/// Creates a ShaderInput instance.
		public function ShaderInput ();
	}
}
