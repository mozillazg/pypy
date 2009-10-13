package flash.display
{
	import flash.geom.Matrix;
	import flash.display.Shader;

	/// Defines a shader fill.
	public class GraphicsShaderFill extends Object implements IGraphicsFill, IGraphicsData
	{
		/// A matrix object (of the flash.geom.Matrix class), which you can use to define transformations on the shader.
		public var matrix : Matrix;
		/// The shader to use for the fill.
		public var shader : Shader;

		/// Creates a new GraphicsShaderFill object.
		public function GraphicsShaderFill (shader:Shader = null, matrix:Matrix = null);
	}
}
