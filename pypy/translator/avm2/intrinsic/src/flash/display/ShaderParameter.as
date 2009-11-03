package flash.display
{
	/// A ShaderParameter instance represents a single input parameter of a shader kernel.
	public class ShaderParameter extends Object
	{
		/// The zero-based index of the parameter.
		public function get index () : int;

		/// The data type of the parameter as defined in the shader.
		public function get type () : String;

		/// The value or values that are passed in as the parameter value to the shader.
		public function get value () : Array;
		public function set value (v:Array) : void;

		/// Creates a ShaderParameter instance.
		public function ShaderParameter ();
	}
}
