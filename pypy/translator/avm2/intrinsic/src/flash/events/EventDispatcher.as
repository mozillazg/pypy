package flash.events
{
	import flash.events.Event;
	import flash.events.IEventDispatcher;

	/**
	 * [broadcast event] Dispatched when Flash Player loses operating system focus and is becoming inactive.
	 * @eventType flash.events.Event.DEACTIVATE
	 */
	[Event(name="deactivate", type="flash.events.Event")] 

	/**
	 * [broadcast event] Dispatched when Flash Player gains operating system focus and becomes active.
	 * @eventType flash.events.Event.ACTIVATE
	 */
	[Event(name="activate", type="flash.events.Event")] 

	/// The EventDispatcher class implements the IEventDispatcher interface and is the base class for the DisplayObject class.
	public class EventDispatcher extends Object implements IEventDispatcher
	{
		/// Registers an event listener object with an EventDispatcher object so that the listener receives notification of an event.
		public function addEventListener (type:String, listener:Function, useCapture:Boolean = false, priority:int = 0, useWeakReference:Boolean = false) : void;

		/// Dispatches an event into the event flow.
		public function dispatchEvent (event:Event) : Boolean;

		/// Aggregates an instance of the EventDispatcher class.
		public function EventDispatcher (target:IEventDispatcher = null);

		/// Checks whether the EventDispatcher object has any listeners registered for a specific type of event.
		public function hasEventListener (type:String) : Boolean;

		/// Removes a listener from the EventDispatcher object.
		public function removeEventListener (type:String, listener:Function, useCapture:Boolean = false) : void;

		public function toString () : String;

		/// Checks whether an event listener is registered with this EventDispatcher object or any of its ancestors for the specified event type.
		public function willTrigger (type:String) : Boolean;
	}
}
