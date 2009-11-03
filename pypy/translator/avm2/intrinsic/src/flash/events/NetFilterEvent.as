package flash.events
{
	import flash.utils.ByteArray;
	import flash.events.Event;

	public class NetFilterEvent extends Event
	{
		public var data : ByteArray;
		public var header : ByteArray;

		public function clone () : Event;

		public function NetFilterEvent (type:String, bubbles:Boolean = false, cancelable:Boolean = false, header:ByteArray = null, data:ByteArray = null);

		public function toString () : String;
	}
}
