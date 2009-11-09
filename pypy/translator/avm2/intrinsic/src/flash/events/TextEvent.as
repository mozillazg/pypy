package flash.events
{
	import flash.events.Event;

	/// Flash Player dispatches TextEvent objects when a user enters text in a text field or clicks a hyperlink in an HTML-enabled text field.
	public class TextEvent extends Event
	{
		/// Defines the value of the type property of a link event object.
		public static const LINK : String = "link";
		/// Defines the value of the type property of a textInput event object.
		public static const TEXT_INPUT : String = "textInput";

		/// For a textInput event, the character or sequence of characters entered by the user.
		public function get text () : String;
		public function set text (value:String) : void;

		/// Creates a copy of the TextEvent object and sets the value of each property to match that of the original.
		public function clone () : Event;

		/// Constructor for TextEvent objects.
		public function TextEvent (type:String, bubbles:Boolean = false, cancelable:Boolean = false, text:String = "");

		/// Returns a string that contains all the properties of the TextEvent object.
		public function toString () : String;
	}
}
