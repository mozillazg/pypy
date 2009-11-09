package flash.events
{
	/// The EventPhase class provides values for the eventPhase property of the Event class.
	public class EventPhase extends Object
	{
		/// The target phase, which is the second phase of the event flow.
		public static const AT_TARGET : uint;
		/// The bubbling phase, which is the third phase of the event flow.
		public static const BUBBLING_PHASE : uint;
		/// The capturing phase, which is the first phase of the event flow.
		public static const CAPTURING_PHASE : uint;

		public function EventPhase ();
	}
}
