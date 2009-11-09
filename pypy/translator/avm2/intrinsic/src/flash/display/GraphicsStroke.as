package flash.display
{
	import flash.display.IGraphicsFill;

	/// Defines a line style or stroke.
	public class GraphicsStroke extends Object implements IGraphicsStroke, IGraphicsData
	{
		/// Specifies the instance containing data for filling a stroke.
		public var fill : IGraphicsFill;
		/// Indicates the limit at which a miter is cut off.
		public var miterLimit : Number;
		/// Specifies whether to hint strokes to full pixels.
		public var pixelHinting : Boolean;
		/// Indicates the thickness of the line in points; valid values are 0-255.
		public var thickness : Number;

		/// Specifies the type of caps at the end of lines.
		public function get caps () : String;
		public function set caps (value:String) : void;

		/// Specifies the type of joint appearance used at angles.
		public function get joints () : String;
		public function set joints (value:String) : void;

		/// Specifies the stroke thickness scaling.
		public function get scaleMode () : String;
		public function set scaleMode (value:String) : void;

		/// Creates a new GraphicsStroke object.
		public function GraphicsStroke (thickness:Number = NaN, pixelHinting:Boolean = false, scaleMode:String = "normal", caps:String = "none", joints:String = "round", miterLimit:Number = 3, fill:IGraphicsFill = null);
	}
}
