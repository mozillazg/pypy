package flash.events
{
	import flash.events.Event;

	/// Flash Player dispatches StatusEvent objects when a device, such as a camera or microphone, or an object such as a LocalConnection object reports its status.
	public class StatusEvent extends Event
	{
		/// Defines the value of the type property of a status event object.
		public static const STATUS : String = "status";

		/// A description of the object's status.
		public function get code () : String;
		public function set code (value:String) : void;

		/// The category of the message, such as "status", "warning" or "error".
		public function get level () : String;
		public function set level (value:String) : void;

		/// Creates a copy of the StatusEvent object and sets the value of each property to match that of the original.
		public function clone () : Event;

		/// Constructor for StatusEvent objects.
		public function StatusEvent (type:String, bubbles:Boolean = false, cancelable:Boolean = false, code:String = "", level:String = "");

		/// Returns a string that contains all the properties of the StatusEvent object.
		public function toString () : String;
	}
}
