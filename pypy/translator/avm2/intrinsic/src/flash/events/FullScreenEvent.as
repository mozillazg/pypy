package flash.events
{
	import flash.events.Event;

	/// Flash Player dispatches a FullScreenEvent object whenever the Stage enters or leaves full-screen display mode.
	public class FullScreenEvent extends ActivityEvent
	{
		/// The FullScreenEvent.FULL_SCREEN constant defines the value of the type property of a fullScreen event object.
		public static const FULL_SCREEN : String = "fullScreen";

		/// Indicates whether the Stage object is in full-screen mode (true) or not (false).
		public function get fullScreen () : Boolean;

		/// Creates a copy of a FullScreenEvent object and sets the value of each property to match that of the original.
		public function clone () : Event;

		/// Constructor for FullScreenEvent objects.
		public function FullScreenEvent (type:String, bubbles:Boolean = false, cancelable:Boolean = false, fullScreen:Boolean = false);

		/// Returns a string that contains all the properties of the FullScreenEvent object.
		public function toString () : String;
	}
}
