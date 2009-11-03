package flash.display
{
	import flash.utils.ByteArray;
	import flash.display.ShaderData;

	/// A Shader instance represents a pixel shader in ActionScript.
	public class Shader extends Object
	{
		/// The raw shader bytecode for this Shader instance.
		public function set byteCode (code:ByteArray) : void;

		/// Provides access to parameters, input images, and metadata for the Shader instance.
		public function get data () : ShaderData;
		public function set data (p:ShaderData) : void;

		/// The precision of math operations performed by the shader.
		public function get precisionHint () : String;
		public function set precisionHint (p:String) : void;

		/// Creates a new Shader instance.
		public function Shader (code:ByteArray = null);
	}
}
