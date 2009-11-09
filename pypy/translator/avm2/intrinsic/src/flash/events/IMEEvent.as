package flash.events
{
	import flash.events.Event;

	/// Flash Player dispatches IMEEvent objects when a user enters text using an input method editor (IME).
	public class IMEEvent extends TextEvent
	{
		/// Defines the value of the type property of an imeComposition event object.
		public static const IME_COMPOSITION : String = "imeComposition";

		/// Creates a copy of the IMEEvent object and sets the value of each property to match that of the original.
		public function clone () : Event;

		/// Constructor for IMEEvent objects.
		public function IMEEvent (type:String, bubbles:Boolean = false, cancelable:Boolean = false, text:String = "");

		/// Returns a string that contains all the properties of the IMEEvent object.
		public function toString () : String;
	}
}
