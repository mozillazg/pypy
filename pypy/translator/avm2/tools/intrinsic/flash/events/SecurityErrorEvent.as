package flash.events
{
	import flash.events.Event;

	/// Flash Player dispatches SecurityErrorEvent objects to report the occurrence of a security error.
	public class SecurityErrorEvent extends ErrorEvent
	{
		/// The SecurityErrorEvent.SECURITY_ERROR constant defines the value of the type property of a securityError event object.
		public static const SECURITY_ERROR : String = "securityError";

		/// Creates a copy of the SecurityErrorEvent object and sets the value of each property to match that of the original.
		public function clone () : Event;

		/// Constructor for SecurityErrorEvent objects.
		public function SecurityErrorEvent (type:String, bubbles:Boolean = false, cancelable:Boolean = false, text:String = "");

		/// Returns a string that contains all the properties of the SecurityErrorEvent object.
		public function toString () : String;
	}
}
