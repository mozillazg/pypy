package flash.events
{
	import flash.display.InteractiveObject;
	import flash.events.Event;

	/// Flash Player dispatches MouseEvent objects into the event flow whenever mouse events occur.
	public class MouseEvent extends Event
	{
		/// Defines the value of the type property of a click event object.
		public static const CLICK : String = "click";
		/// Defines the value of the type property of a doubleClick event object.
		public static const DOUBLE_CLICK : String = "doubleClick";
		/// Defines the value of the type property of a mouseDown event object.
		public static const MOUSE_DOWN : String = "mouseDown";
		/// Defines the value of the type property of a mouseMove event object.
		public static const MOUSE_MOVE : String = "mouseMove";
		/// Defines the value of the type property of a mouseOut event object.
		public static const MOUSE_OUT : String = "mouseOut";
		/// Defines the value of the type property of a mouseOver event object.
		public static const MOUSE_OVER : String = "mouseOver";
		/// Defines the value of the type property of a mouseUp event object.
		public static const MOUSE_UP : String = "mouseUp";
		/// Defines the value of the type property of a mouseWheel event object.
		public static const MOUSE_WHEEL : String = "mouseWheel";
		/// Defines the value of the type property of a rollOut event object.
		public static const ROLL_OUT : String = "rollOut";
		/// Defines the value of the type property of a rollOver event object.
		public static const ROLL_OVER : String = "rollOver";

		/// Indicates whether the Alt key is active (true) or inactive (false).
		public function get altKey () : Boolean;
		public function set altKey (value:Boolean) : void;

		/// Indicates whether the primary mouse button is pressed (true) or not (false).
		public function get buttonDown () : Boolean;
		public function set buttonDown (value:Boolean) : void;

		/// Indicates whether the Control key is active (true) or inactive (false).
		public function get ctrlKey () : Boolean;
		public function set ctrlKey (value:Boolean) : void;

		/// Indicates how many lines should be scrolled for each unit the user rotates the mouse wheel.
		public function get delta () : int;
		public function set delta (value:int) : void;

		/// Indicates whether the relatedObject property was set to null for security reasons.
		public function get isRelatedObjectInaccessible () : Boolean;
		public function set isRelatedObjectInaccessible (value:Boolean) : void;

		/// The horizontal coordinate at which the event occurred relative to the containing sprite.
		public function get localX () : Number;
		public function set localX (value:Number) : void;

		/// The vertical coordinate at which the event occurred relative to the containing sprite.
		public function get localY () : Number;
		public function set localY (value:Number) : void;

		/// A reference to a display list object that is related to the event.
		public function get relatedObject () : InteractiveObject;
		public function set relatedObject (value:InteractiveObject) : void;

		/// Indicates whether the Shift key is active (true) or inactive (false).
		public function get shiftKey () : Boolean;
		public function set shiftKey (value:Boolean) : void;

		/// The horizontal coordinate at which the event occurred in global Stage coordinates.
		public function get stageX () : Number;

		/// The vertical coordinate at which the event occurred in global Stage coordinates.
		public function get stageY () : Number;

		/// Creates a copy of the MouseEvent object and sets the value of each property to match that of the original.
		public function clone () : Event;

		/// Constructor for MouseEvent objects.
		public function MouseEvent (type:String, bubbles:Boolean = true, cancelable:Boolean = false, localX:Number = null, localY:Number = null, relatedObject:InteractiveObject = null, ctrlKey:Boolean = false, altKey:Boolean = false, shiftKey:Boolean = false, buttonDown:Boolean = false, delta:int = 0);

		/// Returns a string that contains all the properties of the MouseEvent object.
		public function toString () : String;

		/// Instructs Flash Player to render after processing of this event completes, if the display list has been modified.
		public function updateAfterEvent () : void;
	}
}
