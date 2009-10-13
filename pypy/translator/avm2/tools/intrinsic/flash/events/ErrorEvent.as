package flash.events
{
	import flash.events.Event;

	/// Flash Player dispatches ErrorEvent objects when an error causes a network operation to fail.
	public class ErrorEvent extends TextEvent
	{
		/// Defines the value of the type property of an error event object.
		public static const ERROR : String = "error";

		/// Creates a copy of the ErrorEvent object and sets the value of each property to match that of the original.
		public function clone () : Event;

		/// Constructor for ErrorEvent objects.
		public function ErrorEvent (type:String, bubbles:Boolean = false, cancelable:Boolean = false, text:String = "");

		/// Returns a string that contains all the properties of the ErrorEvent object.
		public function toString () : String;
	}
}
