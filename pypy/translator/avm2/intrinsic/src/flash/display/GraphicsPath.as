package flash.display
{
	/// A collection of drawing commands and the coordinate parameters for those commands.
	public class GraphicsPath extends Object implements IGraphicsPath, IGraphicsData
	{
		/// The Vector of drawing commands as integers representing the path.
		public var commands : Vector.<int>;
		/// The Vector of Numbers containing the parameters used with the drawing commands.
		public var data : Vector.<Number>;

		/// Specifies the winding rule using a value defined in the GraphicsPathWinding class.
		public function get winding () : String;
		public function set winding (value:String) : void;

		/// Adds a new "curveTo" command to the commands vector and new coordinates to the data vector.
		public function curveTo (controlX:Number, controlY:Number, anchorX:Number, anchorY:Number) : void;

		/// Creates a new GraphicsPath object.
		public function GraphicsPath (commands:Vector.<int> = null, data:Vector.<Number> = null, winding:String = "evenOdd");

		/// Adds a new "lineTo" command to the commands vector and new coordinates to the data vector.
		public function lineTo (x:Number, y:Number) : void;

		/// Adds a new "moveTo" command to the commands vector and new coordinates to the data vector.
		public function moveTo (x:Number, y:Number) : void;

		/// Adds a new "wideLineTo" command to the commands vector and new coordinates to the data vector.
		public function wideLineTo (x:Number, y:Number) : void;

		/// Adds a new "wideMoveTo" command to the commands vector and new coordinates to the data vector.
		public function wideMoveTo (x:Number, y:Number) : void;
	}
}
