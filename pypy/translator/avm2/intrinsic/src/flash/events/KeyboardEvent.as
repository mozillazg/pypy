package flash.events
{
	import flash.events.Event;

	/// Flash Player dispatches KeyboardEvent objects in response to user input through a keyboard.
	public class KeyboardEvent extends Event
	{
		/// Defines the value of the type property of a keyDown event object.
		public static const KEY_DOWN : String = "keyDown";
		/// Defines the value of the type property of a keyUp event object.
		public static const KEY_UP : String = "keyUp";

		/// Indicates whether the Alt key is active (true) or inactive (false).
		public function get altKey () : Boolean;
		public function set altKey (value:Boolean) : void;

		/// Contains the character code value of the key pressed or released.
		public function get charCode () : uint;
		public function set charCode (value:uint) : void;

		/// Indicates whether the Control key is active (true) or inactive (false).
		public function get ctrlKey () : Boolean;
		public function set ctrlKey (value:Boolean) : void;

		/// The key code value of the key pressed or released.
		public function get keyCode () : uint;
		public function set keyCode (value:uint) : void;

		/// Indicates the location of the key on the keyboard.
		public function get keyLocation () : uint;
		public function set keyLocation (value:uint) : void;

		/// Indicates whether the Shift key modifier is active (true) or inactive (false).
		public function get shiftKey () : Boolean;
		public function set shiftKey (value:Boolean) : void;

		/// Creates a copy of the KeyboardEvent object and sets the value of each property to match that of the original.
		public function clone () : Event;

		/// Constructor for KeyboardEvent objects.
		public function KeyboardEvent (type:String, bubbles:Boolean = true, cancelable:Boolean = false, charCode:uint = 0, keyCode:uint = 0, keyLocation:uint = 0, ctrlKey:Boolean = false, altKey:Boolean = false, shiftKey:Boolean = false);

		/// Returns a string that contains all the properties of the KeyboardEvent object.
		public function toString () : String;

		/// Instructs Flash Player to render after processing of this event completes, if the display list has been modified
		public function updateAfterEvent () : void;
	}
}
