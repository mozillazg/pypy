package flash.display
{
	import flash.utils.ByteArray;

	/// A ShaderData object contains properties representing any parameters and inputs for a shader kernel, as well as properties containing any metadata specified for the shader.
	public class ShaderData extends Object
	{
		/// Creates a ShaderData instance.
		public function ShaderData (byteCode:ByteArray);
	}
}
