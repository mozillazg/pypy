package flash.events
{
	import flash.events.Event;

	/// The Event class is used as the base class for the creation of Event objects, which are passed as parameters to event listeners when an event occurs.
	public class Event extends Object
	{
		/// The Event.ACTIVATE constant defines the value of the type property of an activate event object.
		public static const ACTIVATE : String = "activate";
		/// The Event.ADDED constant defines the value of the type property of an added event object.
		public static const ADDED : String = "added";
		/// The Event.ADDED_TO_STAGE constant defines the value of the type property of an addedToStage event object.
		public static const ADDED_TO_STAGE : String = "addedToStage";
		/// The Event.CANCEL constant defines the value of the type property of a cancel event object.
		public static const CANCEL : String = "cancel";
		/// The Event.CHANGE constant defines the value of the type property of a change event object.
		public static const CHANGE : String = "change";
		/// Defines the value of the type property of a clear event object.
		public static const CLEAR : String = "clear";
		/// The Event.CLOSE constant defines the value of the type property of a close event object.
		public static const CLOSE : String = "close";
		/// The Event.COMPLETE constant defines the value of the type property of a complete event object.
		public static const COMPLETE : String = "complete";
		/// The Event.CONNECT constant defines the value of the type property of a connect event object.
		public static const CONNECT : String = "connect";
		/// Defines the value of the type property of a copy event object.
		public static const COPY : String = "copy";
		/// Defines the value of the type property of a cut event object.
		public static const CUT : String = "cut";
		/// The Event.DEACTIVATE constant defines the value of the type property of a deactivate event object.
		public static const DEACTIVATE : String = "deactivate";
		/// The Event.ENTER_FRAME constant defines the value of the type property of an enterFrame event object.
		public static const ENTER_FRAME : String = "enterFrame";
		/// Defines the value of the type property of an exitFrame event object.
		public static const EXIT_FRAME : String = "exitFrame";
		/// Defines the value of the type property of an frameConstructed event object.
		public static const FRAME_CONSTRUCTED : String = "frameConstructed";
		/// The Event.FULL_SCREEN constant defines the value of the type property of a fullScreen event object.
		public static const FULLSCREEN : String = "fullscreen";
		/// The Event.ID3 constant defines the value of the type property of an id3 event object.
		public static const ID3 : String = "id3";
		/// The Event.INIT constant defines the value of the type property of an init event object.
		public static const INIT : String = "init";
		/// The Event.MOUSE_LEAVE constant defines the value of the type property of a mouseLeave event object.
		public static const MOUSE_LEAVE : String = "mouseLeave";
		/// The Event.OPEN constant defines the value of the type property of an open event object.
		public static const OPEN : String = "open";
		/// Defines the value of the type property of a paste event object.
		public static const PASTE : String = "paste";
		/// The Event.REMOVED constant defines the value of the type property of a removed event object.
		public static const REMOVED : String = "removed";
		/// The Event.REMOVED_FROM_STAGE constant defines the value of the type property of a removedFromStage event object.
		public static const REMOVED_FROM_STAGE : String = "removedFromStage";
		/// The Event.RENDER constant defines the value of the type property of a render event object.
		public static const RENDER : String = "render";
		/// The Event.RESIZE constant defines the value of the type property of a resize event object.
		public static const RESIZE : String = "resize";
		/// The Event.SCROLL constant defines the value of the type property of a scroll event object.
		public static const SCROLL : String = "scroll";
		/// The Event.SELECT constant defines the value of the type property of a select event object.
		public static const SELECT : String = "select";
		/// Defines the value of the type property of a selectAll event object.
		public static const SELECT_ALL : String = "selectAll";
		/// The Event.SOUND_COMPLETE constant defines the value of the type property of a soundComplete event object.
		public static const SOUND_COMPLETE : String = "soundComplete";
		/// The Event.TAB_CHILDREN_CHANGE constant defines the value of the type property of a tabChildrenChange event object.
		public static const TAB_CHILDREN_CHANGE : String = "tabChildrenChange";
		/// The Event.TAB_ENABLED_CHANGE constant defines the value of the type property of a tabEnabledChange event object.
		public static const TAB_ENABLED_CHANGE : String = "tabEnabledChange";
		/// The Event.TAB_INDEX_CHANGE constant defines the value of the type property of a tabIndexChange event object.
		public static const TAB_INDEX_CHANGE : String = "tabIndexChange";
		/// The Event.UNLOAD constant defines the value of the type property of an unload event object.
		public static const UNLOAD : String = "unload";

		/// Indicates whether an event is a bubbling event.
		public function get bubbles () : Boolean;

		/// Indicates whether the behavior associated with the event can be prevented.
		public function get cancelable () : Boolean;

		/// The object that is actively processing the Event object with an event listener.
		public function get currentTarget () : Object;

		/// The current phase in the event flow.
		public function get eventPhase () : uint;

		/// The event target.
		public function get target () : Object;

		/// The type of event.
		public function get type () : String;

		/// Duplicates an instance of an Event subclass.
		public function clone () : Event;

		/// Used to create new Event object.
		public function Event (type:String, bubbles:Boolean = false, cancelable:Boolean = false);

		/// A utility function for implementing the toString() method in custom ActionScript 3.0 Event classes.
		public function formatToString (className:String, ...rest) : String;

		/// Checks whether the preventDefault() method has been called on the event.
		public function isDefaultPrevented () : Boolean;

		/// Cancels an event's default behavior if that behavior can be canceled.
		public function preventDefault () : void;

		/// Prevents processing of any event listeners in the current node and any subsequent nodes in the event flow.
		public function stopImmediatePropagation () : void;

		/// Prevents processing of any event listeners in nodes subsequent to the current node in the event flow.
		public function stopPropagation () : void;

		/// Returns a string containing all the properties of the Event object.
		public function toString () : String;
	}
}
