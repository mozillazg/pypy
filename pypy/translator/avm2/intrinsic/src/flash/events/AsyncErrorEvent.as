package flash.events
{
	import flash.events.Event;

	/// Flash Player dispatches an AsyncErrorEvent when an exception is thrown from native asynchronous code, which could be from, for example, LocalConnection, NetConnection, SharedObject, or NetStream.
	public class AsyncErrorEvent extends ErrorEvent
	{
		/// The AsyncErrorEvent.ASYNC_ERROR constant defines the value of the type property of an asyncError event object.
		public static const ASYNC_ERROR : String = "asyncError";
		/// The exception that was thrown.
		public var error : Error;

		/// Constructor for AsyncErrorEvent objects.
		public function AsyncErrorEvent (type:String, bubbles:Boolean = false, cancelable:Boolean = false, text:String = "", error:Error = null);

		/// Creates a copy of the AsyncErrorEvent object and sets the value of each property to match that of the original.
		public function clone () : Event;

		/// Returns a string that contains all the properties of the AsyncErrorEvent object.
		public function toString () : String;
	}
}
