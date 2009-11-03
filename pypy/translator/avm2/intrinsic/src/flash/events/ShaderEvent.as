package flash.events
{
	import flash.utils.ByteArray;
	import flash.display.BitmapData;
	import flash.events.Event;

	/// A ShaderEvent is dispatched when a shader operation launched from a ShaderJob finishes.
	public class ShaderEvent extends Event
	{
		/// Defines the value of the type property of a complete event object.
		public static const COMPLETE : String = "complete";

		/// The BitmapData object that was passed to the ShaderJob.start() method.
		public function get bitmapData () : BitmapData;
		public function set bitmapData (bmpData:BitmapData) : void;

		/// The ByteArray object that was passed to the ShaderJob.start() method.
		public function get byteArray () : ByteArray;
		public function set byteArray (bArray:ByteArray) : void;

		/// The Vector.<Number> object that was passed to the ShaderJob.start() method.
		public function get vector () : Vector.<Number>;
		public function set vector (v:Vector.<Number>) : void;

		/// Creates a copy of the ShaderEvent object and sets the value of each property to match that of the original.
		public function clone () : Event;

		/// Creates a ShaderEvent object to pass to event listeners.
		public function ShaderEvent (type:String, bubbles:Boolean = false, cancelable:Boolean = false, bitmap:BitmapData = null, array:ByteArray = null, vector:Vector.<Number> = null);

		/// Returns a string that contains all the properties of the ShaderEvent object.
		public function toString () : String;
	}
}
