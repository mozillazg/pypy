package flash.system
{
	import flash.events.EventDispatcher;

	/**
	 * Dispatched when a user has completed an input method editor (IME) composition and the reading string is available.
	 * @eventType flash.events.IMEEvent.IME_COMPOSITION
	 */
	[Event(name="imeComposition", type="flash.events.IMEEvent")] 

	/// The IME class lets you directly manipulate the operating system's input method editor (IME) in the Flash Player application that is running on a client computer.
	public class IME extends EventDispatcher
	{
		public static function set constructOK (construct:Boolean) : void;

		/// The conversion mode of the current IME.
		public static function get conversionMode () : String;
		public static function set conversionMode (mode:String) : void;

		/// Indicates whether the system IME is enabled (true) or disabled (false).
		public static function get enabled () : Boolean;
		public static function set enabled (enabled:Boolean) : void;

		/// Instructs the IME to select the first candidate for the current composition string.
		public static function doConversion () : void;

		public function IME ();

		/// Sets the IME composition string.
		public static function setCompositionString (composition:String) : void;
	}
}
