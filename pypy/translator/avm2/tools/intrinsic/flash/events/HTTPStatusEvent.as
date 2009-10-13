package flash.events
{
	import flash.events.Event;

	/// The application dispatches HTTPStatusEvent objects when a network request returns an HTTPstatus code.
	public class HTTPStatusEvent extends Event
	{
		/// The HTTPStatusEvent.HTTP_STATUS constant defines the value of the type property of a httpStatus event object.
		public static const HTTP_STATUS : String = "httpStatus";

		/// The HTTP status code returned by the server.
		public function get status () : int;

		/// Creates a copy of the HTTPStatusEvent object and sets the value of each property to match that of the original.
		public function clone () : Event;

		/// Constructor for HTTPStatusEvent objects.
		public function HTTPStatusEvent (type:String, bubbles:Boolean = false, cancelable:Boolean = false, status:int = 0);

		/// Returns a string that contains all the properties of the HTTPStatusEvent object.
		public function toString () : String;
	}
}
