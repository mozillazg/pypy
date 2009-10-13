package flash.events
{
	import flash.events.Event;

	/// The IEventDispatcher interface defines methods for adding or removing event listeners, checks whether specific types of event listeners are registered, and dispatches events.
	public interface IEventDispatcher
	{
		/// Registers an event listener object with an EventDispatcher object so that the listener receives notification of an event.
		public function addEventListener (type:String, listener:Function, useCapture:Boolean = false, priority:int = 0, useWeakReference:Boolean = false) : void;

		/// Dispatches an event into the event flow.
		public function dispatchEvent (event:Event) : Boolean;

		/// Checks whether the EventDispatcher object has any listeners registered for a specific type of event.
		public function hasEventListener (type:String) : Boolean;

		/// Removes a listener from the EventDispatcher object.
		public function removeEventListener (type:String, listener:Function, useCapture:Boolean = false) : void;

		/// Checks whether an event listener is registered with this EventDispatcher object or any of its ancestors for the specified event type.
		public function willTrigger (type:String) : Boolean;
	}
}
