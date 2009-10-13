package flash.events
{
	import flash.display.InteractiveObject;
	import flash.events.Event;

	/// Flash Player dispatches FocusEvent objects when the user changes the focus from one object in the display list to another.
	public class FocusEvent extends Event
	{
		/// Defines the value of the type property of a focusIn event object.
		public static const FOCUS_IN : String = "focusIn";
		/// Defines the value of the type property of a focusOut event object.
		public static const FOCUS_OUT : String = "focusOut";
		/// Defines the value of the type property of a keyFocusChange event object.
		public static const KEY_FOCUS_CHANGE : String = "keyFocusChange";
		/// Defines the value of the type property of a mouseFocusChange event object.
		public static const MOUSE_FOCUS_CHANGE : String = "mouseFocusChange";

		/// Indicates whether the relatedObject property was set to null for security reasons.
		public function get isRelatedObjectInaccessible () : Boolean;
		public function set isRelatedObjectInaccessible (value:Boolean) : void;

		/// The key code value of the key pressed to trigger a keyFocusChange event.
		public function get keyCode () : uint;
		public function set keyCode (value:uint) : void;

		/// A reference to the complementary InteractiveObject instance that is affected by the change in focus.
		public function get relatedObject () : InteractiveObject;
		public function set relatedObject (value:InteractiveObject) : void;

		/// Indicates whether the Shift key modifier is activated, in which case the value is true.
		public function get shiftKey () : Boolean;
		public function set shiftKey (value:Boolean) : void;

		/// Creates a copy of the FocusEvent object and sets the value of each property to match that of the original.
		public function clone () : Event;

		/// Constructor for FocusEvent objects.
		public function FocusEvent (type:String, bubbles:Boolean = true, cancelable:Boolean = false, relatedObject:InteractiveObject = null, shiftKey:Boolean = false, keyCode:uint = 0);

		/// Returns a string that contains all the properties of the FocusEvent object.
		public function toString () : String;
	}
}
