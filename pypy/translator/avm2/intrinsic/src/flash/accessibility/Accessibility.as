package flash.accessibility
{
	import flash.display.DisplayObject;

	/// The Accessibility class manages communication with screen readers.
	public class Accessibility extends Object
	{
		/// Indicates whether a screen reader is currently active and the player is communicating with it.
		public static function get active () : Boolean;

		public function Accessibility ();

		public static function sendEvent (source:DisplayObject, childID:uint, eventType:uint, nonHTML:Boolean = false) : void;

		/// Tells Flash Player to apply any accessibility changes made by using the DisplayObject.accessibilityProperties property.
		public static function updateProperties () : void;
	}
}
