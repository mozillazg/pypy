package flash.text.engine
{
	import flash.display.DisplayObject;
	import flash.text.engine.ElementFormat;
	import flash.events.EventDispatcher;

	/// The GraphicElement class represents a graphic element in a TextBlock or GroupElement object.
	public class GraphicElement extends ContentElement
	{
		/// The height in pixels to reserve for the graphic in the line.
		public function get elementHeight () : Number;
		public function set elementHeight (value:Number) : void;

		/// The width in pixels to reserve for the graphic in the line.
		public function get elementWidth () : Number;
		public function set elementWidth (value:Number) : void;

		/// The DisplayObject to be used as a graphic for the GraphicElement.
		public function get graphic () : DisplayObject;
		public function set graphic (value:DisplayObject) : void;

		/// Creates a new GraphicElement instance.
		public function GraphicElement (graphic:DisplayObject = null, elementWidth:Number = 15, elementHeight:Number = 15, elementFormat:ElementFormat = null, eventMirror:EventDispatcher = null, textRotation:String = "rotate0");
	}
}
