package flash.display
{
	/// Defines a solid fill.
	public class GraphicsSolidFill extends Object implements IGraphicsFill, IGraphicsData
	{
		/// Indicates the alpha transparency value of the fill.
		public var alpha : Number;
		/// The color of the fill.
		public var color : uint;

		/// Creates a new GraphicsSolidFill object.
		public function GraphicsSolidFill (color:uint = 0, alpha:Number = 1);
	}
}
